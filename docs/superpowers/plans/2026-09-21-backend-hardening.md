# Backend Hardening Plan (review of 2026-09-21)

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. Run the backend suite after every task:
> `cd backend && uv run --no-project --python 3.12 --with-requirements requirements.txt --with-requirements requirements-dev.txt -- python -m pytest -q -p no:cacheprovider`
> Baseline before any change: **100 passed**.

**Goal:** Fix every backend finding from the 2026-09-21 review before the Stripe work ([2026-09-19-stripe-payments.md](2026-09-19-stripe-payments.md)) lands on top of it.

**Scope:** Backend and deployment only. Frontend is reviewed separately. The one frontend touchpoint (admin cancel `notify` flag, Task 5) is optional and backwards compatible.

---

## Corrections to the review

I re-checked every finding before planning. Several changed:

| Review finding | Now | Why |
|---|---|---|
| Empty `ADMIN_TOKEN_SECRET` — *Critical* | **Medium** (fail-fast guard) | Production already has the `admin-token-secret` secret set. The risk is a future misconfigured deploy, not a live hole. |
| Admin edit `setattr` without validation — *Critical* | **Medium** | Only a logged-in admin can reach it. It's a data-integrity and 500-error problem, not privilege escalation. |
| No CSRF on booking-action POST — *High* | **Withdrawn** | The signed token *is* the authorization, and the action page loads no external resources, so there's no Referer leak. Cheap headers are still added in Task 8. |
| Rate limiter: "point it at PostgreSQL" | **Suggested fix was wrong** | flask-limiter's storage backends are memory, Redis, Memcached, MongoDB and etcd. There's no Postgres backend, and you already declined Redis. Task 9 replaces it with a small DB-backed login throttle. |
| Advisory lock missing on admin create — *Medium* | **Withdrawn** | Skipping availability checks on admin create is documented, intended behaviour. |

New findings from the re-check:

| Finding | Severity |
|---|---|
| **Dependency CVEs** (pip-audit): flask 3.0.3 → fix 3.1.3; flask-cors 4.0.0 → 6 advisories, fix 6.0.0; python-dotenv 1.0.1 → fix 1.2.2 | **High** |
| Public booking accepts any `sujeito`/`regime`/`tipo_consulta`/`local_consulta`. Price and duration are derived from those values, which matters once Stripe charges from `compute_price()` | **High** |
| Admin cancel emails the nutritionist *"A seguinte consulta foi cancelada **pelo cliente**"* when she cancelled it herself | **Medium** (bug) |
| Malformed input returns 500 instead of 400: `int()` query params, `date.fromisoformat()` in admin filters, `None.strip()` when `email` is `null`, a JSON array body | **Medium** |
| "Consulta Atualizada" email says *tu/acede* while every other email says *você/aceda* | Low |
| `SITE_URL` default is the dead `ibnutricao.pt` domain; `inesbandarranutricao@gmail.com` is hardcoded 5× in templates | Low |
| `smtplib.SMTP` has no timeout, so a hung SMTP server holds one of the 2 gunicorn workers for up to 60 s | Low |
| Container runs as root | Low |
| `localhost` CORS origins are allowed in production | Low |

Checked and **not** a problem: email header injection via `nome`/`subject`. Every subject contains "—", so Python encodes the whole header and any CR/LF stays inert inside the encoding (verified with Python's `email` package).

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `backend/requirements.txt` | Modify | Upgrade flask, flask-cors, python-dotenv, gunicorn |
| `backend/app.py` | Modify | Secret guard, input helpers, public enum validation, TZ fix, CORS, headers |
| `backend/validation.py` | **Create** | Shared enums, length caps and parse helpers (public + admin) |
| `backend/admin_routes.py` | Modify | Validate create/edit, 400 on bad filters, cancel email fix, session renewal |
| `backend/auth.py` | Modify | Shorter lifetimes, sliding renewal, action-token slot check |
| `backend/booking_action_routes.py` | Modify | Reject actions on past slots, security headers |
| `backend/email_service.py` | Modify | Tone fix, address constant, SMTP timeout, `SITE_URL` default |
| `backend/models.py` | Modify | `utcnow()` replacement, `LoginAttempt` model (Task 9) |
| `backend/holidays_pt.py` | Modify | Warn outside covered years |
| `backend/Dockerfile` | Modify | Non-root user |
| `docker-compose.yml` | Modify | `CORS_ALLOW_LOCALHOST=true` for local dev |
| `backend/tests/*` | Modify / add | One test per behaviour change |

---

### Task 1: Upgrade vulnerable dependencies — HIGH

**Files:** `backend/requirements.txt`

- [ ] Bump to at least: `flask==3.1.3`, `flask-cors==6.0.0` (or latest 6.x), `python-dotenv==1.2.2`, `gunicorn==23.0.0`. Pin exact resolved versions.
- [ ] Check the flask-cors 6 changes: path matching became case-sensitive and ordered by specificity. We only pass `origins=[...]` app-wide, so no code change is expected.
- [ ] Re-run `uvx pip-audit -r backend/requirements.txt`. It must report 0 vulnerabilities.
- [ ] Run the tests.

---

### Task 2: Fail fast on missing secrets — MEDIUM

**Files:** `backend/app.py` (after the `app.config[...]` block, ~line 65)

```python
for key in ("ADMIN_TOKEN_SECRET", "ADMIN_PASSWORD_HASH"):
    if not app.config[key]:
        raise RuntimeError(f"{key} must be set")
if len(app.config["ADMIN_TOKEN_SECRET"]) < 32:
    raise RuntimeError("ADMIN_TOKEN_SECRET must be at least 32 characters")
```

- [ ] `conftest.py` sets both variables before importing `app`, so tests still import. Its test secret `"unit-test-secret-key"` is only 20 characters: lengthen it to 32 or more.
- [ ] **Before deploying:** run the Azure check in *Azure changes → A*. If the production secret is shorter than 32 characters, this guard crash-loops the new revision.

---

### Task 3: Shared validation module + public enum checks — HIGH

**Files:** create `backend/validation.py`; modify `backend/app.py` `create_booking`

Move `EMAIL_RE`, `BOOKING_LIMITS` and `_too_long` out of `app.py`, and add the enums. The values mirror `website/src/constants/booking.js`. A test pins them so the two lists can't drift silently:

```python
SUJEITOS = ("adulto", "bebé")
REGIMES = ("presencial", "online")
TIPOS_CONSULTA = {
    "adulto": ("consulta de pré-concepção", "consulta na gravidez",
               "consulta no pós-parto", "consulta gestão de peso"),
    "bebé": ("introdução alimentar", "seletividade alimentar", "nutrição pediátrica"),
}
CLINICS = ("Clínica Manus (Angra do Heroísmo)",
           "Centro de Psicologia Flávia Bessa (Angra do Heroísmo)")
STATUSES = ("pendente", "confirmado", "revisao", "cancelado")

def s(data, key):
    """String field or "" — never raises on null / number / list."""
    v = data.get(key)
    return v.strip() if isinstance(v, str) else ""
```

In `create_booking`, after the length check:
- [ ] `sujeito.lower()` must be in `SUJEITOS`, `regime.lower()` in `REGIMES`, and `tipo_consulta` in `TIPOS_CONSULTA[sujeito]`. Otherwise return 400 `invalid_choice` with the field name.
- [ ] If presencial, `local_consulta` must be in `CLINICS`.
- [ ] `is_first` must be a real `bool`. `bool("false")` is currently `True`. Reject non-bools with 400.
- [ ] Replace the `data["x"].strip()` calls with `s(data, "x")`.
- [ ] Tests: each enum rejected; a valid booking still returns 201. Update `test_bookings.py` payloads that use values outside the enums.

> Pricing is still client-declared through `is_first` (primeira vs seguimento). That's a product decision already listed in the Stripe plan's open questions, so it isn't changed here.

---

### Task 4: 400 instead of 500 on malformed input — MEDIUM

**Files:** `backend/validation.py`, `backend/app.py`, `backend/admin_routes.py`

Add `int_arg(name, default, lo, hi)` and `date_arg(name)` helpers. Each raises a small `BadInput` exception that an `@app.errorhandler(BadInput)` turns into `400 {"error": "invalid_<field>"}`.

- [ ] Every JSON route: replace `request.get_json(force=True) or {}` with `json_body()`, which returns 400 unless the body is a dict (`get_json(force=True, silent=True)`).
- [ ] `/api/availability`: `duration` → `int_arg("duration", 60, 30, 180)`.
- [ ] `/api/availability/month`: also bound `year` to 2020–2100. `date(99999, …)` currently raises.
- [ ] Admin `list_bookings` / `stats_view`: `page`, `per_page`, `date_from`, `date_to`.
- [ ] Public `cancel_booking` / `edit_request`: `email` via `s()`. Cap `message` at 2000 characters.
- [ ] Tests: one per endpoint sending garbage and asserting 400.

---

### Task 5: Validate admin create/edit; fix the admin cancel email — MEDIUM

**Files:** `backend/admin_routes.py`

**Edit and create validation.** Admin is deliberately more lenient than public: legacy rows (e.g. `sujeito="Bebé"`, `tipo_consulta="Pós-parto"` in the test fixtures) must stay editable.
- [ ] `status` must be in `STATUSES`, and `regime.lower()` in `REGIMES`.
- [ ] ~~`sujeito.lower()` must be in `SUJEITOS`~~ Dropped during implementation: the admin modal edits `sujeito` as free text (`EditBookingModal.jsx:7`), so it gets a length check only.
- [ ] `price` must be a number from 0 to 1000; `duration_minutes` an int from 15 to 240.
- [ ] `email` must match `EMAIL_RE`.
- [ ] Every string gets the `BOOKING_LIMITS` caps.
- [ ] `tipo_consulta` and `local_consulta`: length check only.
- [ ] `slot_date`/`slot_time` go through the same parse helpers as create. Today a bad value in edit raises a 500.
- [ ] Validate **everything before the first `setattr`**, so a rejected edit never half-applies.

**Cancel.** Change `cancel_booking_admin`:
- [ ] Remove `send_nutritionist_cancellation`: she triggered the cancel, and the email wrongly says the client did.
- [ ] Accept `notify` (default `True`, matching edit). Send the client email only when it's true. The current admin UI omits the flag, so behaviour is unchanged until the frontend passes it.
- [ ] Tests: `test_admin_cancel_delete.py`: no nutritionist email; `notify=false` sends nothing.

---

### Task 6: Timezone correctness — MEDIUM

**Files:** `backend/app.py`, `backend/admin_routes.py`, `backend/models.py`

Slots are Azores local time; the container runs in UTC.
- [ ] Add `now_azores()` to `calendar_service.py`, returning naive local time. It already has `TIMEZONE`.
- [ ] Public cancel check (`app.py:395`): compare the slot against `now_azores()`, not `utcnow()`.
- [ ] `date.today()` in both availability endpoints becomes `now_azores().date()`.
- [ ] `created_at` / `updated_at`: replace `datetime.utcnow` with `lambda: datetime.now(timezone.utc).replace(tzinfo=None)`. Storage stays naive UTC, so **no schema change**. This clears the 172 deprecation warnings.

---

### Task 7: Token lifetimes — HIGH

**Files:** `backend/auth.py`, `backend/admin_routes.py`, `backend/booking_action_routes.py`

- [ ] `BOOKING_ACTION_MAX_AGE` 45 → **7 days** (changed from 14 at your request, 2026-09-21).
- [ ] `action_page` / `action_execute`: if the booking's slot is already in the past (`now_azores()`), show *"Esta consulta já passou"* and do nothing. A link can't act on history.
- [ ] `TOKEN_MAX_AGE` 30 → **7 days**, with sliding renewal:
  - [ ] Add an `@admin_bp.after_request` hook. When a valid admin cookie is present and older than 24 h (`loads(..., return_timestamp=True)`), re-issue it. Active use keeps her logged in; a stolen cookie dies 7 days after last use.
- [ ] Tests: expired action token → "Ligação inválida"; past slot → no-op; cookie older than 24 h is re-issued; cookie older than 7 days → 401.

> Revoking every admin session today means rotating `ADMIN_TOKEN_SECRET`, which also kills every pending email action link. That's acceptable at this scale, so they aren't split. If you ever want independent revocation, add a separate `BOOKING_ACTION_SECRET`.

---

### Task 8: Security headers — LOW

**Files:** `backend/app.py` (`after_request`), `backend/booking_action_routes.py`

- [ ] Every response: `X-Content-Type-Options: nosniff`.
- [ ] The HTML action pages from `_page()` also get:
  - `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'`
  - `Referrer-Policy: no-referrer`
  - `Cache-Control: no-store`
- [ ] Check whether frontend nginx already sets these globally. That belongs to the frontend review; setting them here too does no harm.

---

### Task 9: Login brute-force throttle that works across workers and replicas — LOW (optional)

Today, `5 per minute` is counted per gunicorn worker × replica (2 workers × up to 3 replicas → up to 30/min) and resets on every deploy. Redis was declined, so use Postgres directly:

**Files:** `backend/models.py`, `backend/admin_routes.py`

- [ ] Add a `LoginAttempt(id, ip, created_at)` model. It's a **new table**, so `db.create_all()` in `entrypoint.sh` creates it on boot. **No manual DDL.**
- [ ] In `login`: if the same IP has 10 or more failures in the last 15 minutes → 429. Record each failure. On success, delete that IP's rows. Also prune rows older than 1 day.
- [ ] Keep the in-memory limiter as the first line.
- [ ] Tests: 11th failure → 429; a success clears the count.

> Skip this task if the admin password is long and random. The throttle only matters against a guessable password.

---

### Task 10: Email consistency and robustness — LOW

**Files:** `backend/email_service.py`

- [ ] `send_booking_updated_client`: switch to the formal register used by the other emails (*a sua consulta*, *Confirme*, *aceda*, *email utilizado nesta marcação*).
- [ ] Replace the 5 hardcoded `inesbandarranutricao@gmail.com` with `{escape(REPLY_TO)}`.
- [ ] `SITE_URL` default → `https://inesbandarranutricao.com`.
- [ ] `smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)`.
- [ ] Tests: snapshot-style assertion that the updated email contains "a sua consulta".

---

### Task 11: CORS and container hardening — LOW

**Files:** `backend/app.py`, `docker-compose.yml`, `backend/Dockerfile`

- [ ] Add the localhost origins only when `CORS_ALLOW_LOCALHOST=true`. Set that in `docker-compose.yml` → `backend.environment`, and in `dev-local/` if it starts the backend itself.
- [ ] Dockerfile: create and switch to a non-root user.
  ```dockerfile
  RUN useradd --system --uid 10001 app && chown -R app /app
  USER app
  ```
  `entrypoint.sh` writes `/app/credentials.json`, so `/app` must stay writable by `app`, which the `chown` covers. Build locally and run `docker compose up` to confirm the entrypoint still materialises credentials.

---

### Task 12: Holiday table expiry — LOW

**Files:** `backend/holidays_pt.py`, `backend/tests/test_holidays.py`

- [ ] `is_holiday()`: log a warning once per year when `query_date.year not in COVERED_YEARS`.
- [ ] Add `test_table_covers_next_year`, asserting `date.today().year + 1 in COVERED_YEARS`. It starts failing in 2028, a year before the table runs out.

---

## Azure changes

Most of this is **code-only**. No new resources and no manual DDL (Task 9's table is created automatically).

**A. Before deploying Task 2:** confirm the secrets exist and are long enough.
```bash
az account set --subscription 8a6d121a-51ff-446b-ab5b-dbce1beae7d0
az containerapp secret list -n ib-backend -g rg-ibnutricao-prod -o table
az containerapp show -n ib-backend -g rg-ibnutricao-prod --query "properties.template.containers[0].env[].{name:name,secret:secretRef,value:value}" -o table
```
`ADMIN_TOKEN_SECRET` and `ADMIN_PASSWORD_HASH` must map to `admin-token-secret` / `admin-password-hash`. If the token secret is under 32 characters, rotate it first. Rotating logs you out of the admin panel and invalidates pending email action links.
```bash
az containerapp secret set -n ib-backend -g rg-ibnutricao-prod --secrets admin-token-secret=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
```

**B. Verify env values used by Tasks 10 and 11:** `SITE_URL` and `FRONTEND_URL` must both be `https://inesbandarranutricao.com`. `CORS_ALLOW_LOCALHOST` must **not** be set in production.

**C. Deploy:** the usual surgical path, backend only.
```bash
az acr login -n acribnutricao
docker build -t acribnutricao.azurecr.io/ibnutricao-backend:20260921-hardening -t acribnutricao.azurecr.io/ibnutricao-backend:latest backend
docker push acribnutricao.azurecr.io/ibnutricao-backend:20260921-hardening
docker push acribnutricao.azurecr.io/ibnutricao-backend:latest
az containerapp update -n ib-backend -g rg-ibnutricao-prod --image acribnutricao.azurecr.io/ibnutricao-backend:20260921-hardening --revision-suffix hardening0921
```

**D. After deploy:**
- [ ] `az containerapp logs show -n ib-backend -g rg-ibnutricao-prod --tail 50`: no `RuntimeError`, "Schema ready." printed.
- [ ] If Task 9 shipped, check that `login_attempts` exists in Postgres.
- [ ] Smoke test: `/api/health`; month availability loads; `/api/availability?date=x&duration=abc` returns **400**; admin login works; a test booking round-trip (book → confirm link → cancel) works.

**Expected one-time side effects:**
- The admin is logged out once: old 30-day cookies older than 7 days are rejected.
- Email action links older than 7 days stop working and show "Ligação inválida".

---

## Suggested order

1 → 2 → 3 → 4 → 5 → 6 → 7 in one PR: security and correctness. 8, 10, 11, 12 can ride along; they're small. 9 is optional. Deploy once, before starting the Stripe plan.

## Not included (deliberately)

- Pending bookings hold a slot indefinitely until she acts. The Stripe plan already covers expiring stale holds.
- Alembic migrations. `create_all` plus one-off SQL is working and documented; revisit if the schema keeps changing.
- General refactors (repeated `from datetime import …` inside functions, duplicated booking lookup). Not required by any finding.
