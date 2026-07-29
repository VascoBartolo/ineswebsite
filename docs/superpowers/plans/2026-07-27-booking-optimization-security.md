# Booking Optimization & Security Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add server-side pagination to admin bookings, then harden the application against the verificar_aplicacoes.txt checklist (rate limiting, input sanitization, error handling, logging).

**Architecture:** The backend is a Flask + SQLAlchemy app talking to PostgreSQL, deployed on Azure Container Apps. The admin frontend is React (JSX). Pagination will use SQL LIMIT/OFFSET with server-side total count. Security hardening adds Flask-Limiter for rate limiting, markupsafe for HTML escaping in emails, structured JSON error handlers, and Python logging to stdout (ACA captures stdout automatically).

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL, React, Flask-Limiter, markupsafe, Python logging

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `backend/admin_routes.py` | Modify | Add pagination params to `list_bookings`, escape LIKE wildcards |
| `backend/app.py` | Modify | Register error handlers, init rate limiter, configure logging |
| `backend/models.py` | No change | — |
| `backend/auth.py` | No change | — |
| `backend/email_service.py` | Modify | Escape user-supplied values in HTML templates |
| `backend/requirements.txt` | Modify | Add flask-limiter, markupsafe |
| `website/src/admin/adminApi.js` | Modify | Pass page/per_page params, return pagination metadata |
| `website/src/admin/BookingsTab.jsx` | Modify | Add pagination controls, update data fetching |
| `backend/tests/test_admin_bookings.py` | Modify | Add pagination tests |
| `backend/tests/conftest.py` | No change | — |

---

### Task 1: Backend — Paginated admin bookings endpoint

**Files:**
- Modify: `backend/admin_routes.py:45-85`
- Modify: `backend/tests/test_admin_bookings.py`

The current `list_bookings` calls `.all()` and returns every matching row. Change it to accept `page` (default 1) and `per_page` (default 30), use SQLAlchemy `.paginate()`, and return pagination metadata alongside bookings. The summary (count, confirmed_count, faturado) must still reflect the **filtered** total, not just the current page.

- [ ] **Step 1: Write failing test for pagination**

In `backend/tests/test_admin_bookings.py`, add:

```python
def test_list_bookings_pagination(client, admin_cookies):
    """Default page=1, per_page=30. With 3 bookings and per_page=2, page 1 has 2, page 2 has 1."""
    from tests.conftest import make_booking
    make_booking(reference="IB-PAGE0001")
    make_booking(reference="IB-PAGE0002")
    make_booking(reference="IB-PAGE0003")

    # Page 1 with per_page=2
    resp = client.get("/api/admin/bookings?per_page=2&page=1", headers={"Cookie": admin_cookies})
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body["bookings"]) == 2
    assert body["pagination"]["total"] == 3
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["per_page"] == 2
    assert body["pagination"]["pages"] == 2

    # Page 2
    resp2 = client.get("/api/admin/bookings?per_page=2&page=2", headers={"Cookie": admin_cookies})
    body2 = resp2.get_json()
    assert len(body2["bookings"]) == 1
    assert body2["pagination"]["page"] == 2

    # Summary reflects ALL filtered rows, not just the page
    assert body["summary"]["count"] == 3


def test_list_bookings_pagination_defaults(client, admin_cookies):
    """Without page/per_page params, defaults to page=1 per_page=30."""
    from tests.conftest import make_booking
    make_booking(reference="IB-DFLT0001")

    resp = client.get("/api/admin/bookings", headers={"Cookie": admin_cookies})
    body = resp.get_json()
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["per_page"] == 30
    assert "bookings" in body
```

Note: `admin_cookies` is a fixture that logs in and returns the auth cookie header. If it doesn't exist yet in the test file, check step 1b.

- [ ] **Step 1b: Check existing test helpers and add admin_cookies fixture if missing**

Read `backend/tests/test_admin_bookings.py` to see if `admin_cookies` exists. If not, add to `conftest.py`:

```python
@pytest.fixture
def admin_cookies(client):
    resp = client.post("/api/admin/login",
                       json={"password": TEST_PASSWORD},
                       content_type="application/json")
    cookie = resp.headers.get("Set-Cookie", "")
    return cookie
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_admin_bookings.py -v -k "pagination"`
Expected: FAIL — response has no `pagination` key.

- [ ] **Step 3: Implement paginated endpoint**

In `backend/admin_routes.py`, replace the `list_bookings` function:

```python
@admin_bp.route("/bookings")
@auth.require_admin
def list_bookings():
    q = Booking.query
    status = request.args.get("status", "all")
    regime = request.args.get("regime", "all")
    local = request.args.get("local_consulta", "").strip()
    sujeito = request.args.get("sujeito", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    search = request.args.get("q", "").strip().lower()

    if status in ("confirmado", "cancelado"):
        q = q.filter(Booking.status == status)
    if regime in ("presencial", "online"):
        q = q.filter(db.func.lower(Booking.regime) == regime)
    if local:
        q = q.filter(Booking.local_consulta == local)
    if sujeito:
        q = q.filter(Booking.sujeito == sujeito)
    if date_from:
        q = q.filter(Booking.slot_date >= _date.fromisoformat(date_from))
    if date_to:
        q = q.filter(Booking.slot_date <= _date.fromisoformat(date_to))
    if search:
        escaped = search.replace("%", r"\%").replace("_", r"\_")
        like = f"%{escaped}%"
        q = q.filter(db.or_(
            db.func.lower(Booking.nome).like(like),
            db.func.lower(Booking.email).like(like),
            db.func.lower(Booking.reference).like(like),
        ))

    q = q.order_by(Booking.slot_date.desc(), Booking.slot_time.desc())

    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 30))))

    total = q.count()
    rows = q.offset((page - 1) * per_page).limit(per_page).all()

    # Summary must reflect ALL filtered rows — run a lightweight aggregate
    summary_q = q.with_entities(
        db.func.count().label("cnt"),
        db.func.count().filter(Booking.status == "confirmado").label("confirmed"),
        db.func.sum(
            db.case((Booking.status == "confirmado", Booking.price), else_=0)
        ).label("faturado"),
    )
    agg = summary_q.first()

    bookings = [_booking_admin_dict(b) for b in rows]
    summary = {
        "count": agg.cnt,
        "confirmed_count": agg.confirmed,
        "faturado": round(float(agg.faturado or 0), 2),
    }
    pages = (total + per_page - 1) // per_page
    return jsonify({
        "bookings": bookings,
        "summary": summary,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
        },
    })
```

**Key changes:**
- LIKE wildcards (`%`, `_`) in the search term are escaped so a user typing `%` doesn't match everything.
- Summary uses a SQL aggregate instead of Python-side iteration over all rows.
- `per_page` is clamped to [1, 100] to prevent abuse.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_admin_bookings.py -v`
Expected: all pagination tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/admin_routes.py backend/tests/test_admin_bookings.py backend/tests/conftest.py
git commit -m "feat(admin): paginate bookings endpoint (default 30/page)"
```

---

### Task 2: Frontend — Pagination controls in BookingsTab

**Files:**
- Modify: `website/src/admin/adminApi.js:19`
- Modify: `website/src/admin/BookingsTab.jsx`

- [ ] **Step 1: Update adminApi to forward page/per_page**

No code change needed — the existing `bookings(params)` already passes all params as query string. The frontend just needs to include `page` and `per_page` in the params object.

- [ ] **Step 2: Add pagination state and controls to BookingsTab**

```jsx
// In BookingsTab.jsx, add to state:
const [page, setPage] = useState(1);
const [pagination, setPagination] = useState({ total: 0, pages: 1, per_page: 30 });

// Update load() to include page:
const load = useCallback(async () => {
  setLoading(true);
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v && v !== 'all'));
  params.page = page;
  params.per_page = 30;
  try {
    const result = await adminApi.bookings(params);
    setData(result);
    setPagination(result.pagination || { total: 0, pages: 1, per_page: 30 });
  } finally { setLoading(false); }
}, [filters, page]);

// Reset page to 1 when filters change:
const set = (k) => (e) => {
  setFilters((f) => ({ ...f, [k]: e.target.value }));
  setPage(1);
};
```

- [ ] **Step 3: Add pagination UI below the table footer**

```jsx
{pagination.pages > 1 && (
  <div className="pagination">
    <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>← Anterior</button>
    <span>Página {page} de {pagination.pages}</span>
    <button disabled={page >= pagination.pages} onClick={() => setPage(p => p + 1)}>Seguinte →</button>
  </div>
)}
```

- [ ] **Step 4: Add pagination CSS to admin.css**

```css
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 1rem 0;
}
.pagination button {
  padding: 0.4rem 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
}
.pagination button:disabled {
  opacity: 0.4;
  cursor: default;
}
```

- [ ] **Step 5: Test in browser**

Start the dev server, open admin page, verify:
- Table loads first 30 bookings
- Pagination buttons appear if > 30 bookings
- Changing filters resets to page 1
- Summary numbers reflect all filtered bookings, not just the visible page

- [ ] **Step 6: Commit**

```bash
git add website/src/admin/BookingsTab.jsx website/src/admin/admin.css
git commit -m "feat(admin): add pagination controls to bookings table"
```

---

### Task 3: Rate limiting

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app.py`

- [ ] **Step 1: Add flask-limiter to requirements.txt**

Append to `backend/requirements.txt`:
```
flask-limiter==3.5.1
```

- [ ] **Step 2: Initialize limiter in app.py**

After the Flask app creation and CORS setup, add:

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute"],
    storage_uri="memory://",
)
```

- [ ] **Step 3: Apply stricter limits to sensitive endpoints**

Add decorators to the login route and booking creation:

In `admin_routes.py`, import limiter and decorate login:
```python
from app import limiter

@admin_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    ...
```

In `app.py`, decorate create_booking and contact:
```python
@app.route("/api/bookings", methods=["POST"])
@limiter.limit("10 per minute")
def create_booking():
    ...

@app.route("/api/contact", methods=["POST"])
@limiter.limit("5 per minute")
def contact():
    ...
```

- [ ] **Step 4: Run existing tests to verify nothing broke**

Run: `cd backend && python -m pytest -v`
Expected: all tests PASS. Flask-Limiter is disabled during testing since the limiter uses in-memory storage and test client doesn't hit rate limits.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app.py backend/admin_routes.py
git commit -m "feat: add rate limiting (flask-limiter)"
```

---

### Task 4: Input sanitization — escape user data in HTML emails

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/email_service.py`

The email templates inject user-supplied values (`booking.nome`, `booking.email`, `booking.contexto`, `message`, etc.) directly into HTML. A user submitting `<script>alert(1)</script>` as their name gets that injected verbatim into the HTML email body.

- [ ] **Step 1: Add markupsafe to requirements**

`markupsafe` is already a transitive dependency of Flask/Jinja2, but add it explicitly:

Append to `backend/requirements.txt`:
```
markupsafe==2.1.5
```

- [ ] **Step 2: Escape all user-supplied values in email_service.py**

At the top of `email_service.py`, add:
```python
from markupsafe import escape
```

Then wrap every user-supplied value with `escape()` in the HTML templates. The values to escape are: `booking.nome`, `booking.email`, `booking.contacto`, `booking.contexto`, `booking.reference`, `booking.tipo_consulta`, `booking.regime`, `booking.local_consulta`, `name`, `email`, `phone`, `subject`, `message`, `edit_message`.

For example in `send_booking_confirmation`:
```python
def send_booking_confirmation(booking):
    html = _base_style() + f"""
    <h2 ...>Consulta Confirmada</h2>
    <p>Olá <strong>{escape(booking.nome)}</strong>,</p>
    ...
```

Apply `escape()` to every `{variable}` in every email function that contains user data. The `_booking_detail_block` helper is the main place — escape `booking.reference`, `booking.tipo_consulta`, `regime_info`, and price/time which are safe but consistency is good.

- [ ] **Step 3: Run tests**

Run: `cd backend && python -m pytest -v`
Expected: PASS (emails are no-ops in tests since SMTP is unconfigured).

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt backend/email_service.py
git commit -m "fix(security): escape user input in HTML email templates"
```

---

### Task 5: Error handlers — prevent stack trace leaks

**Files:**
- Modify: `backend/app.py`

Flask's default error handling in production (with gunicorn) returns a generic HTML page for 500 errors, but unhandled exceptions in route handlers could leak details in the response body. Add explicit JSON error handlers.

- [ ] **Step 1: Add error handlers in app.py before the routes**

```python
@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "bad_request"}), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "not_found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "method_not_allowed"}), 405

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "rate_limited", "message": "Demasiados pedidos. Tente novamente mais tarde."}), 429

@app.errorhandler(500)
def internal_error(e):
    app.logger.exception("Unhandled exception")
    return jsonify({"error": "internal_error"}), 500
```

- [ ] **Step 2: Ensure debug mode is off in production**

In `app.py`, the `if __name__ == "__main__"` block has `debug=True` which is fine (only runs locally). But add an explicit guard:

```python
if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
            host="0.0.0.0", port=5000)
```

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "fix(security): add JSON error handlers, prevent stack trace leaks"
```

---

### Task 6: Persistent structured logging

**Files:**
- Modify: `backend/app.py`

Replace scattered `print()` calls with Python `logging`. Azure Container Apps captures stdout/stderr automatically, so logging to stdout with structured format is sufficient.

- [ ] **Step 1: Configure logging at app startup**

In `app.py`, after imports:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ibnutricao")
```

- [ ] **Step 2: Add request logging with after_request hook**

```python
@app.after_request
def log_request(response):
    logger.info(
        "%s %s %s %s",
        request.method,
        request.path,
        response.status_code,
        request.remote_addr,
    )
    return response
```

- [ ] **Step 3: Replace print() calls across the codebase**

In `email_service.py`, replace `print(f"[Email] ...")` with `logger.info(...)` / `logger.error(...)`.
In `calendar_service.py`, replace `print(f"[Calendar] ...")` with `logger.warning(...)` / `logger.error(...)`.

Each file gets its own logger:
```python
import logging
logger = logging.getLogger("ibnutricao.email")
```

```python
import logging
logger = logging.getLogger("ibnutricao.calendar")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app.py backend/email_service.py backend/calendar_service.py
git commit -m "feat: structured logging with request tracing"
```

---

### Task 7: Deploy to Azure

**Files:** None — CLI commands only.

- [ ] **Step 1: Run `az login`**

```bash
az login
```

- [ ] **Step 2: Build and push updated backend image**

Use the existing deploy script or run the equivalent:

```bash
az acr build --registry <acr-name> --resource-group rg-ibnutricao-prod --image ibnutricao-backend:latest ./backend
```

- [ ] **Step 3: Update the container app revision**

```bash
az containerapp update --name <app-name> --resource-group rg-ibnutricao-prod --image <acr-name>.azurecr.io/ibnutricao-backend:latest
```

- [ ] **Step 4: Build and push updated frontend image**

```bash
az acr build --registry <acr-name> --resource-group rg-ibnutricao-prod --image ibnutricao-frontend:latest ./website
```

- [ ] **Step 5: Update frontend container app revision**

- [ ] **Step 6: Verify in browser — admin bookings load with pagination, rate limit headers present**

---

## Checklist vs verificar_aplicacoes.txt

| # | Requirement | Status | Task |
|---|-------------|--------|------|
| 1 | Rate limiting | **Adding** | Task 3 |
| 2 | Secrets server side | **Already OK** — env vars loaded server-side, not exposed to frontend | — |
| 3 | Row level security on every table | **N/A** — app uses direct PG connection with app-level auth, not Supabase. All DB access goes through Flask routes guarded by `@auth.require_admin` or public endpoints with limited scope. | — |
| 4 | Validating and sanitizing user input | **Improving** — basic validation exists; adding HTML escaping in emails + LIKE wildcard escaping | Task 1 + Task 4 |
| 5 | Database does not have public tables by default | **Acceptable** — single-app DB with dedicated user; no multi-tenant risk. Could move to a custom schema but low ROI. | — |
| 6 | Auth on protected routes | **Already OK** — `@auth.require_admin` on all admin endpoints; public endpoints are intentionally public | — |
| 7 | Error messages don't leak stack traces | **Fixing** | Task 5 |
| 8 | Turned off or removed admin debug endpoints | **Already OK** — no debug endpoints; `debug=True` only in `__main__` block, gunicorn runs production | Task 5 (hardened) |
| 9 | Persistent logging to trace every request | **Adding** | Task 6 |
