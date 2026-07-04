# Admin Dashboard — Design Spec

**Date:** 2026-07-04
**Project:** IB Nutrição booking app (`D:\Other\ineswebsite`)
**Feature:** Secure admin dashboard for the nutritionist to manage bookings and view statistics.

---

## 1. Goal

Give the nutritionist a private, secure admin area where she can:

1. **Log in securely** with a single password (no per-request credentials, no account system).
2. **Manage bookings** — view all bookings in a filterable table, edit them, cancel them, or permanently delete them.
3. **View statistics** — counts, amount charged, and net profit over a filterable time range, broken down by regime (presencial/online) and by presencial location, plus a time-series chart she can switch between consultation count and net profit.

Single user (the nutritionist). Low data volume. Must be responsive on mobile.

---

## 2. Authentication & Security

### Model: password → signed, httpOnly cookie

- **One hardcoded password**, stored server-side **only as a salted hash** (`ADMIN_PASSWORD_HASH`, an ACA secret) generated with Werkzeug's `generate_password_hash` (pbkdf2-sha256). The plaintext password never appears in code, git, env, or logs.
- **Login** (`POST /api/admin/login`) receives `{password}` over HTTPS (TLS-encrypted in transit). Server verifies with `check_password_hash` (constant-time). On failure: generic 401 + a small fixed delay to blunt brute-force. The password is sent exactly once and never stored client-side.
- **Session token**: on success the server issues a token signed with `itsdangerous.URLSafeTimedSerializer` using a separate strong secret `ADMIN_TOKEN_SECRET` (ACA secret). Payload is minimal (`{"role":"admin"}`); expiry enforced on verify (`max_age = 30 days`).
- **Token transport**: set as a cookie —
  `Set-Cookie: admin_token=<token>; HttpOnly; Secure; SameSite=Strict; Path=/api/admin; Max-Age=2592000`.
  - `HttpOnly` → JavaScript cannot read it (XSS cannot exfiltrate).
  - `Secure` → only sent over HTTPS (see dev note below).
  - `SameSite=Strict` → not attached to cross-site requests (kills CSRF); safe because all admin calls are same-origin (browser talks only to the frontend origin; backend is internal-only behind nginx).
- **Guard**: a `@require_admin` decorator on every `/api/admin/*` route (except `login`) reads the cookie, verifies signature + expiry, returns 401 otherwise.
- **Logout** (`POST /api/admin/logout`) clears the cookie (`Max-Age=0`).
- **Session check** (`GET /api/admin/session`) returns `{authenticated: true|false}` for the SPA route guard on load.

`itsdangerous` and `werkzeug` both ship with Flask — **no new backend dependencies**.

### Config / secrets (new)

| Name | Where | Purpose |
|---|---|---|
| `ADMIN_PASSWORD_HASH` | ACA secret + `.env` | pbkdf2 hash of the admin password |
| `ADMIN_TOKEN_SECRET` | ACA secret + `.env` | random key (32+ bytes) that signs session tokens |
| `ADMIN_COOKIE_SECURE` | env (default `true`) | set `false` for local http dev so the cookie is accepted over `http://localhost` |

A helper snippet (documented in the deploy README) generates the hash locally:
`python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YOUR_STRONG_PASSWORD'))"`.

### Rotation

Rotating `ADMIN_TOKEN_SECRET` invalidates all existing sessions immediately. Changing the password = regenerate `ADMIN_PASSWORD_HASH`.

---

## 3. Net profit rule (business logic)

Net profit is computed **per booking**, then aggregated:

```
net_profit(booking) = price * 0.70   if regime == "presencial"
                    = price * 1.00   if regime == "online"
```

- **Faturado** (amount charged) = sum of `price`.
- **Lucro líquido** (net profit) = sum of `net_profit(booking)`.
- Only **confirmed** bookings count toward stats (cancelled excluded from counts and money). Cancelled bookings remain visible (greyed) in the bookings table.

The 0.70 rate lives in one named backend constant (`PRESENCIAL_NET_RATE = 0.70`) so it is trivial to change.

---

## 4. Backend API

All under `/api/admin/`, all guarded by `@require_admin` except `login`. Same-origin (served via nginx `/api/` proxy in prod, vite `/api` proxy in dev), so no CORS changes.

### Auth
- `POST /login` → `{password}` → sets cookie, `{ok:true}` / 401
- `POST /logout` → clears cookie
- `GET /session` → `{authenticated: bool}`

### Bookings
- `GET /bookings` — query params (all optional, combine with AND):
  `status` (confirmado|cancelado|all), `regime` (presencial|online|all), `local_consulta`, `date_from`, `date_to`, `sujeito`, `q` (free-text over nome/email/reference). Returns matching bookings sorted by `slot_date, slot_time` (desc), plus a small summary (`count`, `confirmed_count`, `faturado`).
- `GET /locations` — distinct `local_consulta` values present in the DB (populates the Local filter dropdowns). *(May be folded into the stats/bookings responses instead of a separate call — implementation detail.)*
- `PUT /bookings/<ref>` — edit. **Editable fields:** nome, email, contacto, idade, sujeito, tipo_consulta, regime, local_consulta, slot_date, slot_time, duration_minutes, price, contexto, status. `reference` and `created_at` immutable. On success:
  1. Update DB row (`updated_at` refreshed).
  2. Update the Google Calendar event (update in place via `google_event_id`; if timing/regime/location changed the event is patched — delete+recreate as fallback, storing the new id).
  3. **Email the client** an "updated booking" notice (new email template).
- `POST /bookings/<ref>/cancel` — soft-cancel: `status → cancelado`, remove the calendar event, email **client + nutritionist** (reuse `send_booking_cancelled_client` / `send_nutritionist_cancellation`). No email-match required (admin is trusted).
- `DELETE /bookings/<ref>` — hard-delete: remove calendar event if present, delete the row permanently. No email. Frontend double-confirms.

### Stats
- `GET /stats` — query params: `date_from`, `date_to`, `regime` (all|presencial|online), `local_consulta` (specific|all), `group_by` (day|week|month). Returns:
  - `count` (confirmed bookings in range/filter)
  - `faturado` (sum price), `lucro_liquido` (sum net_profit)
  - `cancelled_count`
  - `by_regime`: `{presencial:{count,faturado,lucro}, online:{count,faturado,lucro}}`
  - `by_location`: list of `{local_consulta, count, faturado, lucro}` (presencial only)
  - `series`: list of `{period_label, count, lucro_liquido}` for the chart, bucketed by `group_by`.

---

## 5. Frontend

React SPA, same app. New routes in `App.jsx`:

- `/admin` — the dashboard (guarded). On mount calls `GET /api/admin/session`; if not authenticated, shows the login screen.
- Login is rendered inline within `/admin` (no separate public route needed). All admin fetches use `credentials: 'include'`.

### Structure (new files under `website/src/admin/`)

- `AdminPage.jsx` — route entry; holds auth state, renders `<AdminLogin/>` or `<AdminDashboard/>`.
- `AdminLogin.jsx` — single password field → `POST /login`; on success re-checks session.
- `AdminDashboard.jsx` — top bar with the **brand icon** (`/images/vermelho.png`, same logo as the public navbar) alongside the "Painel de Administração" wordmark, plus "Terminar sessão"; tab switch (Marcações / Estatísticas). The brand icon also appears on the login screen.
- `BookingsTab.jsx` — filter bar + table + row actions; `EditBookingModal.jsx` for edits; confirm dialogs for cancel/delete.
- `StatsTab.jsx` — filter bar (date range, regime, local, group-by) + KPI cards + chart + breakdowns.
- `MiniBarChart.jsx` — dependency-free SVG/CSS bar chart with the **Nº consultas / Lucro líquido** metric toggle.
- `admin.css` — styling using the site palette (`--red #B94448`, cream `#FDF7F7`, etc.), matching the approved mockups.

### Visual design (approved mockups)

- **Palette matches the public site** (cream background with blush corner gradients, white cards, `#B94448` accents, Georgia serif headings, Jost body).
- **Brand icon** (`/images/vermelho.png`) shown at the top of both the login screen and the dashboard header.
- **Bookings tab:** filter bar (search, Estado, Regime, Local, De/Até) over a table: Ref · Data/Hora (+duration) · Cliente (nome/email/telefone) · Consulta (tipo + sujeito/idade) · Regime/Local · Preço · Estado pill · Ações (✎ edit, ⊘ cancel, 🗑 delete). Cancelled rows greyed with delete-only. Footer summary (counts + faturado).
- **Stats tab:** filters + 4 KPI cards (Marcações · Faturado · **Lucro líquido** highlighted · Canceladas) + a time-series bar chart with the count/profit toggle and day/week/month grouping + Presencial-vs-Online split (net with gross underneath) + per-location net breakdown.

### Mobile responsive (required)

- Filter grids collapse to 1–2 columns; KPI cards wrap to 2×2; the stats two-column grid stacks; the bookings table switches to a stacked card layout (label:value per field) below a breakpoint (~640px) so it stays readable without horizontal scroll. Verified at mobile width before completion.

---

## 6. Edit behavior detail

- The edit modal pre-fills current values. Regime toggles whether `local_consulta` is shown/required (presencial requires a location; online clears it).
- Price and duration are directly editable (admin override — not recomputed), so she can adjust to real-world situations.
- Saving triggers: DB update → calendar sync → client email. If calendar sync or email fails, the DB change still persists and the failure is logged (booking edit is never blocked by a downstream integration hiccup); the API response notes partial failure so the UI can warn.

---

## 7. Deployment

- **Backend image** rebuilt (new admin routes, email template). No new pip deps.
- **Frontend image** rebuilt (admin SPA). No new npm deps (chart is hand-rolled).
- **New ACA secrets** on `ib-backend`: `admin-password-hash`, `admin-token-secret`; env `ADMIN_COOKIE_SECURE=true`.
- Roll new revisions for both apps (same process already documented in `deploy/README.md`).
- nginx already proxies `/api/` → backend; admin routes are under `/api/`, so no nginx change. Confirm `Set-Cookie` passes through the proxy (default behavior; verify in testing).
- **Rides along (unrelated quick change):** `email_service._base_style()` now renders the brand logo (`{SITE_URL}/images/vermelho.png`, alt "IB Nutrição") at the top of every notification email. Already implemented; ships with this backend rebuild. No separate deploy needed.

---

## 8. Out of scope (non-goals)

- Multiple admin users / roles / account management.
- Password reset flows, 2FA, email-based login.
- Editing `reference`; audit logging of admin actions.
- Exporting data (CSV/PDF).
- Expense tracking beyond the fixed 70%/100% net rule.

---

## 9. Testing / verification

- **Backend:** unit-test net-profit aggregation (presencial 70%, online 100%, mixed, cancelled excluded), stats bucketing (day/week/month), and the `@require_admin` guard (no cookie → 401, bad/expired token → 401, valid → 200).
- **Auth flow:** login sets cookie; protected route works with cookie, fails without; logout clears; expired token rejected.
- **Bookings:** edit persists + syncs calendar + emails client; cancel sets status + removes event + emails; hard-delete removes row + event.
- **Stats:** numbers match hand-computed sample across filters (regime, location, date range, group-by).
- **Frontend:** login → both tabs render; filters update table/stats; chart toggle switches metric; responsive layout verified at ~375px mobile width.
- **Live:** after deploy, run the flow against the ACA URL; confirm cookie is `HttpOnly`/`Secure` in devtools.
```
