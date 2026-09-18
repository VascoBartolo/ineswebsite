# RGPD Compliance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the booking application demonstrably compliant with the RGPD and Portuguese law: enforce and record terms acceptance, execute the retention schedule the privacy policy already publishes, give data subjects a self-service export, and put access auditing and breach response on a documented footing.

**Architecture:** Flask + SQLAlchemy + PostgreSQL backend and a React SPA frontend, both on Azure Container Apps (`ib-backend` internal, `ib-frontend` external, resource group `rg-ibnutricao-prod`). Retention runs as a scheduled Azure Container Apps **Job** reusing the backend image. Terms acceptance is enforced server-side in `create_booking` and constrained at the database level. Export is a signed-link flow delivered by email, reusing the `itsdangerous` machinery already used for booking-action links.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL 16, React, Azure Container Apps + ACA Jobs, itsdangerous, pytest

---

## Two constraints that govern everything

**1. There is no migration framework.** `backend/entrypoint.sh:32` runs `db.create_all()`, which creates *missing tables* and never alters existing ones. Adding a column to `bookings` will **not** happen automatically on deploy.

> **Deploy order is load-bearing.** DDL must run against production Postgres **before** the image that references the new columns starts. SQLAlchemy emits every mapped column in its `SELECT`; deploying the model change first produces `UndefinedColumn` on every booking query and takes the whole booking system down.
>
> Correct order, every time: **additive nullable DDL → backfill → verify → deploy code → tighten constraints.**

**2. No in-process schedulers.** The backend runs `gunicorn --workers 2` with `--min-replicas 1 --max-replicas 3`. An APScheduler thread would run in up to 6 processes concurrently and delete data 6 times over. Retention must be an external scheduled job holding an advisory lock.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/models.py` | Modify | Add `terms_accepted`, `terms_accepted_at`, `terms_version`; add `AccessLog`, `RetentionRun` models |
| `backend/app.py` | Modify | Reject bookings without acceptance; export-request endpoint; wire access logging |
| `backend/legal.py` | Create | `TERMS_VERSION` constant, retention windows — single source of truth for policy values |
| `backend/retention.py` | Create | Retention job entrypoint (`python -m retention`), dry-run mode, run report |
| `backend/export_service.py` | Create | Build the art. 15 export payload for an email address |
| `backend/access_log.py` | Create | `record()` helper + query helpers; append-only |
| `backend/auth.py` | Modify | Sign/verify export tokens (new salt); log authentication events |
| `backend/admin_routes.py` | Modify | Log admin reads/writes; expose read-only access-log endpoint |
| `backend/email_service.py` | Modify | Export-ready email; show acceptance in the nutritionist's booking email |
| `backend/requirements.txt` | No change | `itsdangerous` already present transitively via Flask |
| `website/src/pages/BookingPage.jsx` | Modify | Mandatory acceptance checkbox in step 4; subtle export link in the lookup result |
| `website/src/pages/legalInfo.js` | Modify | `TERMS_VERSION`; mirror of retention windows for display |
| `website/src/pages/TermsConditions.jsx` | Modify | Name the RAL entity; Livro de Reclamações wording |
| `website/src/pages/PrivacyPolicy.jsx` | Modify | Retention table must match the job; add export to the rights section |
| `website/src/admin/*` | Modify | Acceptance column; access-log view |
| `docs/compliance/breach-response.md` | Create | Breach procedure, decision tree, templates |
| `docs/compliance/access-audit.md` | Create | What is logged, why, who reviews it |
| `docs/compliance/data-export.md` | Create | The documented DSR procedure |
| `docs/compliance/ropa.md` | Create | Art. 30 record of processing activities |
| `backend/tests/test_terms_acceptance.py` | Create | Gate + backfill semantics |
| `backend/tests/test_retention.py` | Create | Frozen-time retention behaviour |
| `backend/tests/test_export.py` | Create | Scope, throttle, token expiry |
| `backend/tests/test_access_log.py` | Create | Every privileged path writes exactly one entry |

---

# Workstream A — Terms acceptance

**Legal driver:** RGPD art. 13 (inform at collection) and art. 5(2) accountability — you must be able to *demonstrate* the client was informed. Today nothing is captured.

### Task A1: Additive DDL (run first, against production)

Run **before** any code deploy. Columns are nullable at this stage — a `NOT NULL` without a default would fail against existing rows.

```sql
-- Additive, nullable, idempotent. Safe to run twice.
ALTER TABLE bookings
  ADD COLUMN IF NOT EXISTS terms_accepted    BOOLEAN,
  ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS terms_version     VARCHAR(32);

COMMENT ON COLUMN bookings.terms_accepted    IS 'Client accepted Terms + Privacy Policy at booking time. Always TRUE; acceptance is mandatory.';
COMMENT ON COLUMN bookings.terms_accepted_at IS 'UTC instant of acceptance. Backfilled rows carry the original created_at.';
COMMENT ON COLUMN bookings.terms_version     IS 'Version of the documents accepted, so the exact text shown can be reproduced.';
```

- [ ] **Step 1:** Connect and run. Your deployer IP is already allowed by the `deployer` firewall rule created by `deploy/deploy-azure.ps1`; re-run that script's firewall step first if your IP has changed.

```bash
psql "postgresql://ibadmin:<PASSWORD>@psql-ibnutricao-01.postgres.database.azure.com:5432/ibnutricao?sslmode=require"
```

Or without a local `psql`:

```bash
az postgres flexible-server execute -n psql-ibnutricao-01 -u ibadmin -p "<PASSWORD>" -d ibnutricao --querytext "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN, ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMP, ADD COLUMN IF NOT EXISTS terms_version VARCHAR(32);"
```

- [ ] **Step 2:** Verify the columns exist and are nullable.

```sql
SELECT column_name, data_type, is_nullable, column_default
  FROM information_schema.columns
 WHERE table_name = 'bookings'
   AND column_name IN ('terms_accepted','terms_accepted_at','terms_version')
 ORDER BY column_name;
```

### Task A2: Backfill existing bookings

You have confirmed with every existing client that they agreed. Record that as acceptance **at the time they booked**, which is `created_at`.

- [ ] **Step 1:** Count what will change, before changing it.

```sql
SELECT count(*) AS to_backfill,
       min(created_at) AS oldest,
       max(created_at) AS newest,
       count(*) FILTER (WHERE created_at IS NULL) AS missing_created_at
  FROM bookings
 WHERE terms_accepted IS NULL;
```

- [ ] **Step 2:** Take a snapshot you can restore from. Azure Postgres keeps automated backups, but an explicit table copy makes rollback trivial and instant.

```sql
CREATE TABLE bookings_backup_20260909 AS SELECT * FROM bookings;
SELECT count(*) FROM bookings_backup_20260909;   -- must equal SELECT count(*) FROM bookings
```

- [ ] **Step 3:** Backfill. `COALESCE` guards the (unlikely) row with a null `created_at` rather than writing a null acceptance timestamp.

```sql
BEGIN;

UPDATE bookings
   SET terms_accepted    = TRUE,
       terms_accepted_at = COALESCE(created_at, updated_at, NOW() AT TIME ZONE 'UTC'),
       terms_version     = 'pre-2026-09-09'
 WHERE terms_accepted IS NULL;

-- Expect 0.
SELECT count(*) AS still_null FROM bookings WHERE terms_accepted IS NULL;

COMMIT;
```

> `terms_version = 'pre-2026-09-09'` is deliberate and honest: these clients agreed, but not by ticking a box against a specific published version. Keeping them distinguishable from `v1` acceptances means the record never overstates what happened. Do not merge the two values.

- [ ] **Step 4:** Verify the distribution.

```sql
SELECT terms_version, terms_accepted, count(*),
       min(terms_accepted_at) AS earliest,
       max(terms_accepted_at) AS latest
  FROM bookings
 GROUP BY terms_version, terms_accepted
 ORDER BY terms_version;
```

### Task A3: Model change

- [ ] **Step 1:** In `backend/models.py`, add to `Booking`:

```python
    # Proof the client was shown and accepted the Terms + Privacy Policy before
    # booking (art. 13 information duty, art. 5(2) accountability). Acceptance is
    # mandatory, so terms_accepted is never False on a stored row — the DB check
    # constraint enforces that. `terms_version` records WHICH text was accepted,
    # so the exact wording can be reproduced years later.
    terms_accepted = db.Column(db.Boolean, nullable=False, default=True)
    terms_accepted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    terms_version = db.Column(db.String(32), nullable=False)
```

- [ ] **Step 2:** Add all three to `to_dict()` so they surface in the API, the admin view and the export.

### Task A4: Server-side gate

The checkbox is a UX affordance; the server is the control.

- [ ] **Step 1:** Create `backend/legal.py`:

```python
# Bump whenever the published Terms or Privacy Policy text changes materially.
# Must stay in lockstep with TERMS_VERSION in website/src/pages/legalInfo.js.
TERMS_VERSION = "v1-2026-09-09"
```

- [ ] **Step 2:** In `create_booking` (`backend/app.py`), immediately after the `missing` fields check:

```python
    if data.get("terms_accepted") is not True:
        return jsonify({
            "error": "terms_not_accepted",
            "message": "É necessário aceitar os Termos e Condições e a Política de Privacidade.",
        }), 422
```

Set on the `Booking(...)` construction: `terms_accepted=True`, `terms_accepted_at=datetime.utcnow()`, `terms_version=legal.TERMS_VERSION`.

> Take the timestamp **server-side**. A client-supplied timestamp is unverifiable and worthless as evidence.

- [ ] **Step 3:** Add `"terms_accepted"` to the `required` list so a missing field is a 400 rather than silently falsy.

### Task A5: Frontend — mandatory checkbox

- [ ] **Step 1:** Add `TERMS_VERSION` to `website/src/pages/legalInfo.js`, matching `backend/legal.py`.

- [ ] **Step 2:** Add `termsAccepted: false` to the initial form state, and render in **step 4** (Dados Pessoais), directly above the submit row:

```jsx
<label className="terms-consent">
  <input
    type="checkbox"
    checked={form.termsAccepted}
    onChange={e => setField('termsAccepted', e.target.checked)}
    required
  />
  <span>
    Li e aceito os <Link to="/termos-e-condicoes" target="_blank">Termos e Condições</Link> e a{' '}
    <Link to="/politica-de-privacidade" target="_blank">Política de Privacidade</Link>, incluindo o
    tratamento dos dados de saúde que partilhar para efeitos da consulta. Tratando-se de consulta
    destinada a menor, declaro ser titular das responsabilidades parentais ou estar autorizado.
  </span>
</label>
```

- [ ] **Step 3:** Extend the step-4 branch of `canProceed()`:

```js
if (step === 4) return !!(form.nome && form.idade && form.email && form.contacto && form.termsAccepted);
```

This disables **Confirmar Marcação** until it is ticked.

- [ ] **Step 4:** Send `terms_accepted: form.termsAccepted` in the POST body.
- [ ] **Step 5:** Handle the new `422 terms_not_accepted` in the submit error path, using the server's message.

> **This is the one place a link leaves the footer.** That is deliberate and required: art. 13 obliges you to inform *at the point of collection*, and the booking form is where health data is collected. `target="_blank"` keeps the half-filled form intact.

### Task A6: Surface it everywhere the record is read

- [ ] Admin bookings table: an "Aceitação" column showing date and version.
- [ ] Nutritionist's new-booking email: one line, `Termos aceites: {date} ({version})`.
- [ ] Include all three fields in the data export (Workstream C).

### Task A7: Tighten the database (only after A1–A6 are deployed and green)

```sql
ALTER TABLE bookings
  ALTER COLUMN terms_accepted    SET NOT NULL,
  ALTER COLUMN terms_accepted_at SET NOT NULL,
  ALTER COLUMN terms_version     SET NOT NULL;

-- Acceptance is mandatory, so a stored non-acceptance is a bug, not a state.
-- Makes the invariant impossible to violate even from a future code path.
ALTER TABLE bookings
  ADD CONSTRAINT bookings_terms_accepted_chk CHECK (terms_accepted IS TRUE);
```

- [ ] **Step 1:** Run the above. **Step 2:** Confirm a booking still succeeds end to end. **Step 3:** Drop `bookings_backup_20260909` once satisfied (keep it at least a week).

### Task A8: Tests (`backend/tests/test_terms_acceptance.py`)

- [ ] POST without `terms_accepted` → 400, no row created.
- [ ] POST with `terms_accepted: false` → 422, no row created.
- [ ] POST with `terms_accepted: true` → 201; row has `terms_accepted is True`, a server-side timestamp, and the current `TERMS_VERSION`.
- [ ] A client-supplied `terms_accepted_at` in the payload is **ignored**.
- [ ] `to_dict()` exposes all three fields.

---

# Workstream B — Data retention

**Legal driver:** art. 5(1)(e) storage limitation. The published policy already commits to specific periods and nothing enforces them — a documented, self-evidencing breach.

### Task B0: Settle one question before writing code

> **Is this database the clinical record, or only the scheduling system?**
>
> - **Scheduling only** (clinical notes live elsewhere) → the app holds identity, contact and one free-text `contexto`. Purge aggressively: 12–24 months.
> - **The clinical record of truth** → the minimum clinical retention (≥5 years after last contact) applies to the whole row and every window below must lengthen.
>
> The published retention table assumes the first reading for most categories. **Do not implement B1 until this is answered** — it changes every number.

### Task B1: Encode the schedule

- [ ] Add to `backend/legal.py` as the single source of truth mirrored by the policy page:

```python
RETENTION = {
    # Cancelled / needs-revision bookings never became a consultation: no clinical
    # or fiscal reason to keep them once the dispute window has passed.
    "abandoned_bookings_days": 365,
    # The health free-text is the most sensitive field and the least needed later.
    # Stripped from completed bookings ahead of the row itself.
    "contexto_days": 365,
    # Identity + amount kept for the fiscal period; the row is anonymised, not
    # deleted, so historical statistics survive.
    "anonymise_after_days": 1825,   # 5 years — revisit per B0
    "access_log_days": 365,
    "calendar_event_days": 365,
}
```

### Task B2: The job (`backend/retention.py`)

- [ ] **Step 1:** Runnable with `python -m retention`, taking `--dry-run` (default **on**; require `--apply` to mutate).

- [ ] **Step 2:** Take a Postgres advisory lock so two runs cannot interleave:

```sql
SELECT pg_try_advisory_lock(4820261);   -- exit cleanly if not acquired
```

- [ ] **Step 3:** Passes, in order:

```sql
-- Pass 1 — delete abandoned bookings older than the window.
DELETE FROM bookings
 WHERE status IN ('cancelado','revisao')
   AND slot_date < (CURRENT_DATE - INTERVAL '365 days');

-- Pass 2 — strip the health free-text past the clinical window.
UPDATE bookings
   SET contexto = NULL
 WHERE contexto IS NOT NULL
   AND slot_date < (CURRENT_DATE - INTERVAL '365 days');

-- Pass 3 — anonymise beyond the fiscal window, preserving aggregate value.
UPDATE bookings
   SET nome = 'ANONIMIZADO', email = concat('anon+', id, '@invalid'),
       contacto = '', idade = '', contexto = NULL
 WHERE slot_date < (CURRENT_DATE - INTERVAL '1825 days')
   AND nome <> 'ANONIMIZADO';

-- Pass 4 — prune the access log.
DELETE FROM access_log WHERE created_at < (NOW() - INTERVAL '365 days');
```

> `email` is `NOT NULL` and is the lookup key, so anonymisation writes a syntactically valid but undeliverable per-row `@invalid` address. Do **not** reuse a single constant — it would collide across rows and let one export return another person's history.

- [ ] **Step 4:** Pass 5 — **Google Calendar.** Events carry `Contexto`, name, email and phone in the description (`calendar_service.py:275`) and persist indefinitely. Add `purge_past_events(before_date)` to `calendar_service` deleting `[IB]`-prefixed events older than the window. **Purging the DB while leaving the calendar untouched achieves nothing.**

- [ ] **Step 5:** Every run writes a `RetentionRun` row: started/finished, dry-run flag, per-pass counts, errors. This is your evidence that the policy executes.

### Task B3: Schedule it as an ACA Job

```bash
az containerapp job create \
  --name ib-retention --resource-group rg-ibnutricao-prod \
  --environment "/subscriptions/8a6d121a-51ff-446b-ab5b-dbce1beae7d0/resourceGroups/parcel-rg/providers/Microsoft.App/managedEnvironments/parcel-env" \
  --trigger-type Schedule --cron-expression "0 3 * * 0" \
  --replica-timeout 1800 --replica-retry-limit 1 \
  --image acribnutricao.azurecr.io/ibnutricao-backend:<tag> \
  --registry-server acribnutricao.azurecr.io \
  --cpu 0.25 --memory 0.5Gi \
  --command "python" --args "-m,retention,--apply"
```

- [ ] Weekly, Sunday 03:00 — retention is not time-critical and a weekly cadence keeps the blast radius of a bug small.
- [ ] The job needs the same `DATABASE_URL` and Google secrets as `ib-backend`. Copy the secret **references**, never the values.
- [ ] Trigger manually in dry-run first: `az containerapp job start -n ib-retention -g rg-ibnutricao-prod`.

### Task B4: Tests (`backend/tests/test_retention.py`)

- [ ] Dry-run mutates nothing and still reports accurate counts.
- [ ] A cancelled booking one day inside the window survives; one day outside is deleted.
- [ ] `contexto` is nulled without touching the rest of the row.
- [ ] Anonymised rows keep `price`, `regime`, `slot_date` so statistics are unchanged.
- [ ] Anonymised emails are unique per row.
- [ ] Running twice is idempotent — the second run reports zero changes.

---

# Workstream C — Data export (art. 15 / art. 20)

### Task C0: One design decision, stated plainly

You asked for export "for the past month". As the **data scope** that would not satisfy art. 15, which entitles the subject to *all* personal data held about them — a one-month slice would be a non-compliant access mechanism, and worse than none because it looks like one.

**Recommended reading — and what this plan implements:** the export covers **everything** held for that email address; "past month" becomes the **throttle** (one export per email per 30 days), which art. 12(5) expressly permits for repetitive requests. Abuse resistance without breaking the right.

- [ ] Confirm this interpretation before implementing.

### Task C1: Flow

Reference + email is adequate to *view* one booking. It is **not** adequate to release a full health-data history — reference codes get forwarded, screenshotted and guessed. So the export is never returned inline; it is delivered to the verified address.

```
[Verificar Marcação result]
   └─ subtle link: "Descarregar os meus dados"
        └─ POST /api/bookings/<ref>/export-request   { email }
             ├─ validates ref+email exactly as /lookup does
             ├─ rate limit 3/hour/IP + one per email per 30 days
             ├─ writes an access_log entry
             └─ emails a signed link, valid 24h, to the email ON FILE
                  └─ GET /api/exports/<token>
                       ├─ verifies signature + expiry (new itsdangerous salt)
                       ├─ writes an access_log entry
                       └─ returns JSON (art. 20) + printable HTML (art. 15)
```

- [ ] **Step 1:** New salt in `auth.py` — `_EXPORT_SALT = "ib-data-export"`, `EXPORT_MAX_AGE = 60*60*24`. A distinct salt stops export tokens ever being accepted as admin sessions or booking actions, exactly as `_BOOKING_ACTION_SALT` does today.
- [ ] **Step 2:** Respond **identically** whether or not the pair matched. A differing response turns the endpoint into an oracle for which emails have bookings. Always: *"Se os dados corresponderem a uma marcação, receberá um e-mail com os seus dados."*

### Task C2: Payload (`backend/export_service.py`)

Art. 15 requires more than the rows — the accompanying information is part of the right.

- [ ] Every booking for that email: all columns including `terms_accepted*`, `created_at`, `updated_at`, `status`.
- [ ] The art. 15(1) metadata block: purposes, categories of data, recipients (hosting, email, Google), retention periods, the rights list, the right to complain to the CNPD, and the source of the data.
- [ ] That subject's own `access_log` entries.
- [ ] Generated-at timestamp, controller identification block, and the `terms_version` in force.
- [ ] **Excluded:** other people's data, and internal security detail beyond the subject's own entries.

### Task C3: UI — subtle, as asked

- [ ] In the `lookup-result` block of `BookingPage.jsx`, **below** `lr-actions`, a small muted text link — not a button, not a card:

```jsx
<p className="lr-data-rights">
  <button type="button" className="link-subtle" onClick={handleExportRequest}>
    Descarregar os meus dados
  </button>
</p>
```

- [ ] Style at `0.78rem`, `var(--text-muted)`, underlined on hover only. It must read as a footnote beside the cancel/reschedule actions, never compete with them.
- [ ] After submission, replace it in place with the neutral confirmation sentence. No modal.

### Task C4: Documentation (`docs/compliance/data-export.md`)

- [ ] The self-service flow, and the manual fallback for a subject with no booking reference (identity check, one-month deadline, art. 12(3) extension).
- [ ] Where erasure requests go, and which data cannot be erased because tax law requires it.
- [ ] A register of requests received and how they were resolved.
- [ ] Add the mechanism to §10 of the privacy policy.

### Task C5: Tests (`backend/tests/test_export.py`)

- [ ] Wrong email for a valid reference → same neutral response, no email sent, no token issued.
- [ ] Export contains **every** booking for the address, not just the referenced one.
- [ ] A second request inside 30 days is throttled.
- [ ] An expired or tampered token → 400, nothing disclosed.
- [ ] A booking-action token is rejected by the export endpoint (salt separation holds).

---

# Workstream D — Access audit

**Legal driver:** art. 32 (security of processing) and art. 5(2). For special-category data, being able to say *who looked at what, when* is the expected standard.

### Task D1: Table

```sql
CREATE TABLE IF NOT EXISTS access_log (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    actor        VARCHAR(20)  NOT NULL,   -- 'admin' | 'client' | 'system'
    action       VARCHAR(60)  NOT NULL,   -- 'booking.view', 'export.request', ...
    target_ref   VARCHAR(30),             -- booking reference, when applicable
    target_email VARCHAR(200),            -- lowercased subject email, when applicable
    outcome      VARCHAR(20)  NOT NULL,   -- 'ok' | 'denied' | 'not_found' | 'error'
    ip           VARCHAR(64),
    detail       TEXT                     -- filters / result counts. NEVER health data.
);

CREATE INDEX IF NOT EXISTS ix_access_log_created ON access_log (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_access_log_target  ON access_log (target_email, created_at DESC);
```

> **The log must never contain what was read.** No `contexto`, no clinical detail. A verbose audit log is itself a second, less protected copy of the health data. Record identifiers and outcomes only.

### Task D2: Where to hook

- [ ] **`auth.require_admin` is the single choke point** for every admin read — instrument the decorator once and every current and future admin route is covered. Highest-leverage change in this workstream.
- [ ] Login success and failure (failures matter more).
- [ ] Client lookup, cancel, edit-request.
- [ ] Export request and export download.
- [ ] Booking-action link use (`booking_action_routes.py`).
- [ ] Retention job runs.
- [ ] **Granularity:** for `list_bookings`, log the **query** (filters + result count), not one entry per row — a 30-row page must not produce 30 entries. Log per-record entries only when a single record is opened or edited.
- [ ] **Never let logging break a request.** Wrap `access_log.record()` so a failure goes to stdout and is swallowed.

### Task D3: Review and immutability

- [ ] Append-only: no update or delete route. Only the retention job prunes it.
- [ ] A read-only admin tab, filterable by date and email, paginated like `list_bookings`.
- [ ] A monthly review habit — 10 minutes scanning for `denied` outcomes and unusual volume. **An unread log has no security value;** write the cadence into `docs/compliance/access-audit.md` with the reviewer named.
- [ ] Alert threshold: >5 failed admin logins in an hour.

### Task D4: Tests (`backend/tests/test_access_log.py`)

- [ ] Every privileged path writes exactly one entry with the right actor and outcome.
- [ ] A denied request logs `denied` and still returns 401.
- [ ] No entry ever contains `contexto` content.
- [ ] A logging failure does not fail the underlying request.

---

# Workstream E — Breach notification procedure

**Legal driver:** art. 33 (notify the CNPD within 72 hours of awareness), art. 34 (notify subjects on high risk), art. 33(5) (**document every breach, including those you decide not to notify**).

Mostly a written procedure. Its value is that it exists *before* it is needed — at hour zero of a real incident nobody designs a good process.

### Task E1: `docs/compliance/breach-response.md`

- [ ] **Roles.** Inês Bandarra is the controller and the only person who can decide to notify. Vasco is the technical responder. Name a deputy for each — an incident during a holiday is still on the clock.
- [ ] **The clock starts at awareness, not at diagnosis.** 72 hours runs from reasonable certainty that a breach occurred. You do not wait until you understand it fully; art. 33(4) allows notifying in phases.
- [ ] **Detection sources**, all of which exist today:
  - `ib-backend` / `ib-frontend` container logs (`az containerapp logs show`)
  - the `access_log` (Workstream D) — `denied` spikes, off-hours admin access
  - Azure Postgres audit and firewall logs
  - Google account security alerts on the Gmail/Calendar account
  - a client or the nutritionist reporting something wrong
- [ ] **Timeline:**

  | When | Action |
  |---|---|
  | T+0 | Record date/time of awareness in the incident register. Start the clock. |
  | T+1h | Contain: rotate `ADMIN_TOKEN_SECRET` and `ADMIN_PASSWORD_HASH` (invalidates all sessions), rotate the DB password, revoke Google service-account keys, tighten the Postgres firewall. |
  | T+4h | Preserve evidence: snapshot logs and the DB **before** remediation overwrites them. |
  | T+24h | Assess: what data, whose, how many, is it special-category (almost always yes here), is it recoverable. |
  | T+72h | Notify the CNPD unless the assessment concludes risk is unlikely — and **document that reasoning either way**. |
  | After | Notify subjects if high risk. Post-incident review; update controls. |

- [ ] **Decision tree.** Health data is special-category, so the default posture is: notify unless there is a documented reason not to. Encryption at rest alone does not exempt you if the key or an authenticated path was involved.
- [ ] **Templates, pre-written in Portuguese:**
  - CNPD notification per art. 33(3): nature, categories and approximate number of subjects and records, contact point, likely consequences, measures taken. Filed through the CNPD's online form at `cnpd.pt`.
  - Data-subject notification email: plain language — what happened, what it means for them, what you have done, what they should do, who to contact.
  - Holding statement for clients who ask before you have answers.
- [ ] **Incident register** — date of awareness, description, data affected, subjects affected, risk assessment, notified (Y/N + reasoning), remediation, closure date. **Art. 33(5) requires this for breaches you decide are not notifiable too.** It is the first thing a regulator asks for.
- [ ] **Contacts sheet:** CNPD (`geral@cnpd.pt`, +351 213 928 400), the Azure support plan and how to open a Sev-A, Google Workspace support once migrated, the accountant, legal counsel.

### Task E2: Rehearse it

- [ ] One tabletop exercise per year against a written scenario — *"the admin password appears in a public paste"*. Walk the timeline, find the step nobody can actually perform, fix it. Record the date; an untested procedure is a draft.

---

# Workstream F — Legal text to update alongside the code

- [ ] **F1 — RAL entity.** Terms §14 currently links the consumer portal generically. Name the **Ordem dos Nutricionistas**, per your instruction. Lei 144/2015 art. 18.º requires naming the specific entity; before publishing, confirm it appears on the DGC registry of RAL entities, since only registered entities satisfy the article.
- [ ] **F2 — Livro de Reclamações.** Your reading is right for the *physical* book: online consultations have no premises, and the clinics hold their own for in-person work. Note the distinction, though — DL 156/2005 as amended treats the **electronic** complaints book separately, and it generally applies to online service providers regardless of premises. The Terms already link `livroreclamacoes.pt`; confirm you are registered there and keep the physical/electronic distinction explicit so the position is defensible.
- [ ] **F3 — Retention table.** Privacy policy §5 must state exactly what `legal.py` implements. Divergence is worse than an imperfect but honest schedule.
- [ ] **F4 — Purposes table.** Add a row: proof of terms acceptance — art. 6(1)(c) legal obligation / art. 6(1)(f) legitimate interest in evidencing compliance.
- [ ] **F5 — Rights section.** Document the self-service export in §10.
- [ ] **F6 — `CANCELLATION_NOTICE_HOURS = 24`** is still an assumed default and is published as a binding term. Confirm or change it.
- [ ] **F7 — Bump `TERMS_VERSION`** when F1–F5 land, and note in both documents that a prior version applies to earlier bookings.

---

# Workstream G — Remaining gaps not covered above

Carried from the compliance review so nothing is dropped.

- [ ] **G1 — Google Workspace migration. Highest priority of anything in this document.** Production sends health data to `inesbandarranutricao@gmail.com` over SMTP and writes it into that account's Calendar. A consumer Google account has **no art. 28 data processing agreement**, so the privacy policy's claim that processors operate under art. 28 contracts is currently untrue for Google. Migrate to Google Workspace and accept the Cloud Data Processing Addendum. Nothing else here matters as much.
- [ ] **G2 — Record of processing activities (`docs/compliance/ropa.md`).** Mandatory: the art. 30(5) small-organisation exemption does not apply where special-category data is processed.
- [ ] **G3 — Azure DPA.** Confirm the Microsoft Products and Services Data Protection Addendum covers the subscription.
- [ ] **G4 — Self-host the two Google Fonts.** Removes a third-country IP transfer and a disclosure obligation for a few minutes' work.
- [ ] **G5 — Parental responsibility declaration.** Folded into the A5 checkbox wording above.
- [ ] **G6 — Encryption and backups.** Confirm Postgres encryption at rest and the backup retention window; document the restore procedure and test it once.

---

# Sequencing

| Phase | Contents | Why this order |
|---|---|---|
| **0** | A1 → A2 → verify | DDL and backfill must precede any code referencing the columns |
| **1** | A3–A6, F4, F7 → deploy → A7 → A8 | Highest legal urgency: every booking taken today collects health data with no record of informing the client |
| **2** | D1–D4 | The audit log is a dependency of Workstream C, which must log every export |
| **3** | C0 → C1–C5, F5 | Needs the audit log in place |
| **4** | B0 → B1–B4, F3 | Destructive; goes last, after the export exists so a subject can obtain their data before it is purged |
| **5** | E1–E2, F1, F2, F6, G2 | Documents; parallelisable with everything above |
| **Anytime** | G1 | Independent of the code. Start now — longest external lead time |

**Deploy checklist for every phase touching the schema:** run DDL → verify with `information_schema` → backfill → verify counts → build and push a uniquely tagged image → `az containerapp update` → **wait for traffic to reach the new revision** → smoke-test → tighten constraints.

---

# Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Code deployed before DDL | Total booking outage (`UndefinedColumn` on every query) | Phase 0 gate; verify `information_schema` before building the image |
| Backfill overwrites genuine acceptances | Evidence corrupted | `WHERE terms_accepted IS NULL` only; `bookings_backup_20260909` first |
| Retention job deletes too much | Irreversible data loss | Dry-run default, `--apply` required, manual first run, `RetentionRun` report, DB backup before first live run |
| Retention runs concurrently on replicas | Double deletion | ACA Job (not in-process) + `pg_try_advisory_lock` |
| Export leaks to the wrong person | Health-data breach | Never inline; signed 24h token emailed to the address on file; neutral response either way; every request logged |
| Audit log becomes a second copy of health data | Larger breach surface | Identifiers and outcomes only; never `contexto`; pruned at 12 months |
| Terms checkbox pre-ticked or bypassable | Acceptance record worthless | Server-side 422 gate, DB check constraint, server-side timestamp |
| Policy text drifts from code | Self-evidencing breach | `legal.py` is the single source of truth; F3 keeps §5 in step |

---

# Open questions blocking implementation

1. **B0** — is this database the clinical record, or only the scheduling system? Sets every retention window.
2. **C0** — export scope: all data with a 30-day throttle (recommended, art. 15-compliant), or a genuine one-month data window (not compliant as an access mechanism)?
3. **F6** — is 24 hours the real cancellation notice period?
4. **F1** — is the Ordem dos Nutricionistas listed on the DGC RAL registry?
5. **G1** — timeline for the Google Workspace migration, since it gates the truthfulness of processor claims already published.
