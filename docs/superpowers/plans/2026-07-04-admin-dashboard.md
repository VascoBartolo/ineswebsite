# Admin Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a secure, single-password admin dashboard where the nutritionist manages bookings (view/filter/edit/cancel/delete) and views statistics (counts, amount charged, net profit with the presencial-70%/online-100% rule) — matching the site's visual style and responsive on mobile.

**Architecture:** Flask backend gains an `/api/admin/*` Blueprint guarded by a signed-cookie auth layer (`itsdangerous` + Werkzeug hashing — no new deps). Stats are computed as pure Python functions over booking rows (DB-agnostic, fully unit-testable). The React SPA gains an `/admin` route rendering a login screen or a two-tab dashboard that talks to the admin API with `credentials: 'include'`.

**Tech Stack:** Flask 3 / Flask-SQLAlchemy, Werkzeug (`generate_password_hash`/`check_password_hash`), itsdangerous (`URLSafeTimedSerializer`), pytest (new dev dep) with SQLite StaticPool for tests; React 19 + react-router 7, hand-rolled SVG/CSS chart (no chart lib).

**Spec:** `docs/superpowers/specs/2026-07-04-admin-dashboard-design.md`

---

## Testing approach

- **Backend:** strict TDD with `pytest`. A SQLite in-memory DB (StaticPool) via a `conftest.py` app fixture. Pure logic (auth tokens, net profit, stats aggregation) is tested directly; routes are tested through Flask's test client. Google Calendar and SMTP are monkeypatched — no real external calls in tests.
- **Frontend:** the project has no JS test harness and the design was already validated via mockups, so frontend tasks are verified by building and driving the running app through the Claude Preview server (visual + functional checks) rather than adding a test framework. Components are kept small and focused.

---

## File Structure

**Backend (all in `backend/`)**
- `auth.py` *(new)* — password verification, token issue/verify, `require_admin` decorator, cookie helpers. Reads config from `current_app.config`.
- `stats.py` *(new)* — pure functions: `net_profit`, `summarize`, `build_series`. No Flask/DB imports.
- `admin_routes.py` *(new)* — Flask Blueprint (`url_prefix="/api/admin"`) with login/logout/session, bookings list/edit/cancel/delete, stats.
- `calendar_service.py` *(modify)* — extract `_event_body`, add `update_event`.
- `email_service.py` *(modify)* — add `send_booking_updated_client` (brand-logo header already added).
- `app.py` *(modify)* — load admin config from env into `app.config`; register the blueprint.
- `requirements-dev.txt` *(new)* — `pytest`.
- `tests/conftest.py`, `tests/test_auth.py`, `tests/test_stats.py`, `tests/test_admin_bookings.py`, `tests/test_admin_stats.py` *(new)*.

**Frontend (all in `website/src/`)**
- `admin/AdminPage.jsx` *(new)* — route entry; holds auth state; renders login or dashboard.
- `admin/AdminLogin.jsx` *(new)* — password field → login.
- `admin/AdminDashboard.jsx` *(new)* — top bar (brand icon + wordmark + logout) + tab switch.
- `admin/BookingsTab.jsx` *(new)* — filters + table + actions.
- `admin/EditBookingModal.jsx` *(new)* — edit form.
- `admin/StatsTab.jsx` *(new)* — filters + KPIs + chart + breakdowns.
- `admin/MiniBarChart.jsx` *(new)* — SVG/CSS bars + count/profit toggle.
- `admin/adminApi.js` *(new)* — thin fetch wrapper (`credentials:'include'`, JSON, 401 handling).
- `admin/admin.css` *(new)* — styling + responsive.
- `App.jsx` *(modify)* — add `/admin` route.

---

## Config / secrets (new)

| Name | Source | Purpose |
|---|---|---|
| `ADMIN_PASSWORD_HASH` | ACA secret / `.env` | pbkdf2 hash of the admin password |
| `ADMIN_TOKEN_SECRET` | ACA secret / `.env` | signs session tokens (32+ random bytes) |
| `ADMIN_COOKIE_SECURE` | env (default `"true"`) | `"false"` for local http dev |

Generate the hash locally:
`python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('YOUR_STRONG_PASSWORD'))"`

---

# PHASE 1 — Backend

### Task 1: Test harness + app config for testing

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/tests/__init__.py` (empty)
- Create: `backend/tests/conftest.py`
- Modify: `backend/app.py` (add admin config keys)

- [ ] **Step 1: Add dev dependency**

Create `backend/requirements-dev.txt`:
```
pytest==8.2.0
```

- [ ] **Step 2: Load admin config in app.py**

In `backend/app.py`, right after `app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False`, add:
```python
app.config["ADMIN_PASSWORD_HASH"] = os.environ.get("ADMIN_PASSWORD_HASH", "")
app.config["ADMIN_TOKEN_SECRET"] = os.environ.get("ADMIN_TOKEN_SECRET", "")
app.config["ADMIN_COOKIE_SECURE"] = os.environ.get("ADMIN_COOKIE_SECURE", "true").lower() == "true"
```

- [ ] **Step 3: Create the test fixture**

Create `backend/tests/__init__.py` (empty file).

Create `backend/tests/conftest.py`:
```python
import os
import pytest
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash

TEST_PASSWORD = "test-pass-123"

# Set env BEFORE importing app so module-level reads pick these up.
os.environ.setdefault("GOOGLE_CREDENTIALS_FILE", "/nonexistent-so-calendar-is-noop")
os.environ["ADMIN_PASSWORD_HASH"] = generate_password_hash(TEST_PASSWORD)
os.environ["ADMIN_TOKEN_SECRET"] = "unit-test-secret-key"
os.environ["ADMIN_COOKIE_SECURE"] = "false"

from app import app as flask_app  # noqa: E402
from models import db, Booking  # noqa: E402


@pytest.fixture
def app():
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_ENGINE_OPTIONS={
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
        ADMIN_PASSWORD_HASH=generate_password_hash(TEST_PASSWORD),
        ADMIN_TOKEN_SECRET="unit-test-secret-key",
        ADMIN_COOKIE_SECURE=False,
    )
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def make_booking(**overrides):
    from datetime import date, time
    data = dict(
        reference="IB-TEST0001", sujeito="Bebé", tipo_consulta="Pós-parto",
        regime="online", local_consulta=None, nome="Cliente Teste", idade=3,
        email="cliente@teste.pt", contacto="960000000", contexto=None,
        slot_date=date(2026, 7, 15), slot_time=time(16, 0),
        duration_minutes=60, price=50, status="confirmado",
    )
    data.update(overrides)
    b = Booking(**data)
    db.session.add(b)
    db.session.commit()
    return b
```

- [ ] **Step 4: Verify the harness collects**

Run: `cd backend && python -m pytest -q`
Expected: `no tests ran` (0 collected, no import errors).

- [ ] **Step 5: Commit**

```bash
git add backend/requirements-dev.txt backend/tests/__init__.py backend/tests/conftest.py backend/app.py
git commit -m "test: add pytest harness and admin config keys"
```

---

### Task 2: Auth core (`auth.py`) — password + token + decorator

**Files:**
- Create: `backend/auth.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_auth.py`:
```python
import time
import pytest
from conftest import TEST_PASSWORD
import auth


def test_verify_password_correct(app):
    with app.app_context():
        assert auth.verify_password(TEST_PASSWORD) is True


def test_verify_password_wrong(app):
    with app.app_context():
        assert auth.verify_password("nope") is False


def test_token_roundtrip(app):
    with app.app_context():
        token = auth.issue_token()
        assert auth.verify_token(token) is True


def test_token_tampered_rejected(app):
    with app.app_context():
        token = auth.issue_token()
        assert auth.verify_token(token + "x") is False


def test_token_expired_rejected(app):
    with app.app_context():
        token = auth.issue_token()
        # max_age=0 means already expired
        assert auth.verify_token(token, max_age=0) is False
        time.sleep(1)
        assert auth.verify_token(token, max_age=0) is False


def test_verify_none_token(app):
    with app.app_context():
        assert auth.verify_token(None) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_auth.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth'`.

- [ ] **Step 3: Implement `auth.py`**

Create `backend/auth.py`:
```python
import time
from functools import wraps

from flask import current_app, request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash

COOKIE_NAME = "admin_token"
COOKIE_PATH = "/api/admin"
TOKEN_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
_SALT = "ib-admin-session"

# Small fixed delay on failed logins to blunt brute-force.
LOGIN_FAIL_DELAY = 0.4


def _serializer():
    secret = current_app.config.get("ADMIN_TOKEN_SECRET") or ""
    return URLSafeTimedSerializer(secret, salt=_SALT)


def verify_password(password):
    stored = current_app.config.get("ADMIN_PASSWORD_HASH") or ""
    if not stored or not password:
        return False
    return check_password_hash(stored, password)


def issue_token():
    return _serializer().dumps({"role": "admin"})


def verify_token(token, max_age=TOKEN_MAX_AGE):
    if not token:
        return False
    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return False
    return data.get("role") == "admin"


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.cookies.get(COOKIE_NAME)
        if not verify_token(token):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


def set_auth_cookie(response, token):
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=TOKEN_MAX_AGE, path=COOKIE_PATH,
        httponly=True, secure=current_app.config.get("ADMIN_COOKIE_SECURE", True),
        samesite="Strict",
    )
    return response


def clear_auth_cookie(response):
    response.set_cookie(
        COOKIE_NAME, "", max_age=0, path=COOKIE_PATH,
        httponly=True, secure=current_app.config.get("ADMIN_COOKIE_SECURE", True),
        samesite="Strict",
    )
    return response
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_auth.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py backend/tests/test_auth.py
git commit -m "feat: admin auth core (password, signed token, guard)"
```

---

### Task 3: Auth routes (login / logout / session)

**Files:**
- Create: `backend/admin_routes.py`
- Modify: `backend/app.py` (register blueprint)
- Test: `backend/tests/test_admin_auth_routes.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_admin_auth_routes.py`:
```python
from conftest import TEST_PASSWORD


def test_login_success_sets_cookie(client):
    r = client.post("/api/admin/login", json={"password": TEST_PASSWORD})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True
    assert "admin_token" in r.headers.get("Set-Cookie", "")


def test_login_wrong_password(client):
    r = client.post("/api/admin/login", json={"password": "wrong"})
    assert r.status_code == 401


def test_session_false_without_cookie(client):
    r = client.get("/api/admin/session")
    assert r.status_code == 200
    assert r.get_json()["authenticated"] is False


def test_session_true_after_login(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})
    r = client.get("/api/admin/session")
    assert r.get_json()["authenticated"] is True


def test_logout_clears_session(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})
    client.post("/api/admin/logout")
    r = client.get("/api/admin/session")
    assert r.get_json()["authenticated"] is False


def test_protected_route_requires_auth(client):
    r = client.get("/api/admin/bookings")
    assert r.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_admin_auth_routes.py -q`
Expected: FAIL — 404s (blueprint not registered).

- [ ] **Step 3: Create the blueprint with auth routes**

Create `backend/admin_routes.py`:
```python
import time
from flask import Blueprint, request, jsonify

import auth

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True) or {}
    password = data.get("password") or ""
    if not auth.verify_password(password):
        time.sleep(auth.LOGIN_FAIL_DELAY)
        return jsonify({"error": "invalid_credentials"}), 401
    resp = jsonify({"ok": True})
    return auth.set_auth_cookie(resp, auth.issue_token())


@admin_bp.route("/logout", methods=["POST"])
def logout():
    resp = jsonify({"ok": True})
    return auth.clear_auth_cookie(resp)


@admin_bp.route("/session")
def session():
    token = request.cookies.get(auth.COOKIE_NAME)
    return jsonify({"authenticated": auth.verify_token(token)})


@admin_bp.route("/bookings")
@auth.require_admin
def list_bookings():
    # Real implementation in Task 5; placeholder returns empty for now.
    return jsonify({"bookings": [], "summary": {}})
```

Note: the `/bookings` body here is a stub only so the auth test passes; Task 5 replaces it with the real query. (Not a placeholder in the plan sense — Task 5 provides the full code.)

- [ ] **Step 4: Register the blueprint in app.py**

In `backend/app.py`, after `db.init_app(app)`, add:
```python
from admin_routes import admin_bp
app.register_blueprint(admin_bp)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_admin_auth_routes.py -q`
Expected: PASS (6 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/admin_routes.py backend/app.py backend/tests/test_admin_auth_routes.py
git commit -m "feat: admin login/logout/session routes"
```

---

### Task 4: Stats pure functions (`stats.py`)

**Files:**
- Create: `backend/stats.py`
- Test: `backend/tests/test_stats.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_stats.py`:
```python
from datetime import date
import stats


def test_net_profit_presencial_is_70pct():
    assert stats.net_profit("presencial", 100) == 70.0


def test_net_profit_online_is_100pct():
    assert stats.net_profit("online", 50) == 50.0


def _b(regime, price, status="confirmado", local=None, d=date(2026, 7, 1)):
    return {"regime": regime, "price": price, "status": status,
            "local_consulta": local, "slot_date": d}


def test_summarize_counts_and_money():
    rows = [
        _b("presencial", 100, local="Clínica NIITE"),
        _b("online", 50),
        _b("presencial", 100, status="cancelado", local="Clínica NIITE"),
    ]
    s = stats.summarize(rows)
    assert s["count"] == 2
    assert s["cancelled_count"] == 1
    assert s["faturado"] == 150.0
    assert s["lucro_liquido"] == 120.0  # 70 + 50
    assert s["by_regime"]["presencial"]["lucro"] == 70.0
    assert s["by_regime"]["online"]["lucro"] == 50.0
    assert s["by_location"][0]["local_consulta"] == "Clínica NIITE"
    assert s["by_location"][0]["lucro"] == 70.0


def test_build_series_weekly_buckets():
    rows = [
        _b("online", 50, d=date(2026, 7, 1)),
        _b("online", 50, d=date(2026, 7, 2)),
        _b("presencial", 100, d=date(2026, 7, 13)),
    ]
    series = stats.build_series(rows, "week")
    assert len(series) == 2
    assert series[0]["count"] == 2
    assert series[0]["lucro_liquido"] == 100.0
    assert series[1]["lucro_liquido"] == 70.0


def test_build_series_monthly_buckets():
    rows = [_b("online", 50, d=date(2026, 6, 30)), _b("online", 50, d=date(2026, 7, 1))]
    series = stats.build_series(rows, "month")
    assert [x["period"] for x in series] == ["2026-06", "2026-07"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_stats.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'stats'`.

- [ ] **Step 3: Implement `stats.py`**

Create `backend/stats.py`:
```python
PRESENCIAL_NET_RATE = 0.70
ONLINE_NET_RATE = 1.00


def net_profit(regime, price):
    price = float(price)
    if (regime or "").lower() == "presencial":
        return round(price * PRESENCIAL_NET_RATE, 2)
    return round(price * ONLINE_NET_RATE, 2)


def summarize(rows):
    confirmed = [r for r in rows if r["status"] == "confirmado"]
    faturado = round(sum(float(r["price"]) for r in confirmed), 2)
    lucro = round(sum(net_profit(r["regime"], r["price"]) for r in confirmed), 2)

    by_regime = {}
    for reg in ("presencial", "online"):
        subset = [r for r in confirmed if (r["regime"] or "").lower() == reg]
        by_regime[reg] = {
            "count": len(subset),
            "faturado": round(sum(float(r["price"]) for r in subset), 2),
            "lucro": round(sum(net_profit(r["regime"], r["price"]) for r in subset), 2),
        }

    loc_map = {}
    for r in confirmed:
        if (r["regime"] or "").lower() != "presencial":
            continue
        key = r.get("local_consulta") or "—"
        e = loc_map.setdefault(key, {"local_consulta": key, "count": 0, "faturado": 0.0, "lucro": 0.0})
        e["count"] += 1
        e["faturado"] = round(e["faturado"] + float(r["price"]), 2)
        e["lucro"] = round(e["lucro"] + net_profit(r["regime"], r["price"]), 2)
    by_location = sorted(loc_map.values(), key=lambda e: e["lucro"], reverse=True)

    return {
        "count": len(confirmed),
        "cancelled_count": sum(1 for r in rows if r["status"] == "cancelado"),
        "faturado": faturado,
        "lucro_liquido": lucro,
        "by_regime": by_regime,
        "by_location": by_location,
    }


def _period_key(d, group_by):
    if group_by == "day":
        return d.isoformat()
    if group_by == "month":
        return f"{d.year}-{d.month:02d}"
    iso = d.isocalendar()  # (year, week, weekday)
    return f"{iso[0]}-W{iso[1]:02d}"


def build_series(rows, group_by):
    confirmed = [r for r in rows if r["status"] == "confirmado"]
    buckets = {}
    for r in confirmed:
        k = _period_key(r["slot_date"], group_by)
        e = buckets.setdefault(k, {"period": k, "count": 0, "lucro_liquido": 0.0})
        e["count"] += 1
        e["lucro_liquido"] = round(e["lucro_liquido"] + net_profit(r["regime"], r["price"]), 2)
    return [buckets[k] for k in sorted(buckets)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_stats.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/stats.py backend/tests/test_stats.py
git commit -m "feat: net-profit and stats aggregation functions"
```

---

### Task 5: Bookings list route with filters

**Files:**
- Modify: `backend/admin_routes.py` (replace the `/bookings` stub; add a row→dict helper)
- Test: `backend/tests/test_admin_bookings.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_admin_bookings.py`:
```python
from datetime import date, time
from conftest import TEST_PASSWORD, make_booking


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


def test_lists_all_bookings(client, app):
    with app.app_context():
        make_booking(reference="IB-A", email="a@x.pt")
        make_booking(reference="IB-B", email="b@x.pt", regime="presencial",
                     local_consulta="Clínica NIITE")
    _auth(client)
    r = client.get("/api/admin/bookings")
    assert r.status_code == 200
    body = r.get_json()
    assert len(body["bookings"]) == 2
    assert body["summary"]["confirmed_count"] == 2


def test_filter_by_regime(client, app):
    with app.app_context():
        make_booking(reference="IB-A", regime="online")
        make_booking(reference="IB-B", regime="presencial", local_consulta="X")
    _auth(client)
    r = client.get("/api/admin/bookings?regime=presencial")
    refs = [b["reference"] for b in r.get_json()["bookings"]]
    assert refs == ["IB-B"]


def test_filter_by_status_and_search(client, app):
    with app.app_context():
        make_booking(reference="IB-A", nome="Ana Melo", status="confirmado")
        make_booking(reference="IB-B", nome="João Dias", status="cancelado")
    _auth(client)
    assert len(client.get("/api/admin/bookings?status=cancelado").get_json()["bookings"]) == 1
    assert len(client.get("/api/admin/bookings?q=ana").get_json()["bookings"]) == 1


def test_filter_by_date_range(client, app):
    with app.app_context():
        make_booking(reference="IB-A", slot_date=date(2026, 7, 1))
        make_booking(reference="IB-B", slot_date=date(2026, 8, 1))
    _auth(client)
    r = client.get("/api/admin/bookings?date_from=2026-07-15&date_to=2026-07-31")
    assert r.get_json()["bookings"] == [] or all(
        b["slot_date"] >= "2026-07-15" for b in r.get_json()["bookings"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_admin_bookings.py -q`
Expected: FAIL — stub returns empty list, assertions on counts fail.

- [ ] **Step 3: Implement the real bookings list route**

In `backend/admin_routes.py`, add imports at the top (below existing imports):
```python
from datetime import date as _date

from models import db, Booking
```

Replace the stub `list_bookings` function with:
```python
def _booking_admin_dict(b):
    d = b.to_dict()
    d["idade"] = b.idade
    d["duration_minutes"] = b.duration_minutes
    d["updated_at"] = b.updated_at.isoformat() if b.updated_at else None
    return d


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
        like = f"%{search}%"
        q = q.filter(db.or_(
            db.func.lower(Booking.nome).like(like),
            db.func.lower(Booking.email).like(like),
            db.func.lower(Booking.reference).like(like),
        ))

    rows = q.order_by(Booking.slot_date.desc(), Booking.slot_time.desc()).all()
    bookings = [_booking_admin_dict(b) for b in rows]
    confirmed = [b for b in rows if b.status == "confirmado"]
    summary = {
        "count": len(rows),
        "confirmed_count": len(confirmed),
        "faturado": round(sum(float(b.price) for b in confirmed), 2),
    }
    return jsonify({"bookings": bookings, "summary": summary})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_admin_bookings.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/admin_routes.py backend/tests/test_admin_bookings.py
git commit -m "feat: admin bookings list with filters"
```

---

### Task 6: Stats route

**Files:**
- Modify: `backend/admin_routes.py` (add `/stats` + `/locations`)
- Test: `backend/tests/test_admin_stats.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_admin_stats.py`:
```python
from datetime import date
from conftest import TEST_PASSWORD, make_booking


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


def test_stats_totals(client, app):
    with app.app_context():
        make_booking(reference="IB-A", regime="presencial", price=100,
                     local_consulta="Clínica NIITE", slot_date=date(2026, 7, 1))
        make_booking(reference="IB-B", regime="online", price=50, slot_date=date(2026, 7, 2))
        make_booking(reference="IB-C", regime="online", price=50,
                     status="cancelado", slot_date=date(2026, 7, 3))
    _auth(client)
    body = client.get("/api/admin/stats?group_by=week").get_json()
    assert body["count"] == 2
    assert body["faturado"] == 150.0
    assert body["lucro_liquido"] == 120.0
    assert body["cancelled_count"] == 1
    assert len(body["series"]) >= 1


def test_stats_regime_filter(client, app):
    with app.app_context():
        make_booking(reference="IB-A", regime="presencial", price=100, local_consulta="X")
        make_booking(reference="IB-B", regime="online", price=50)
    _auth(client)
    body = client.get("/api/admin/stats?regime=online").get_json()
    assert body["count"] == 1
    assert body["lucro_liquido"] == 50.0


def test_locations_endpoint(client, app):
    with app.app_context():
        make_booking(reference="IB-A", regime="presencial", local_consulta="Clínica NIITE")
        make_booking(reference="IB-B", regime="presencial", local_consulta="Angra")
    _auth(client)
    locs = client.get("/api/admin/locations").get_json()["locations"]
    assert set(locs) == {"Clínica NIITE", "Angra"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_admin_stats.py -q`
Expected: FAIL — 404 (routes not defined).

- [ ] **Step 3: Implement `/stats` and `/locations`**

In `backend/admin_routes.py`, add import near the top:
```python
import stats as stats_mod
```

Add these routes:
```python
@admin_bp.route("/stats")
@auth.require_admin
def stats_view():
    regime = request.args.get("regime", "all")
    local = request.args.get("local_consulta", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    group_by = request.args.get("group_by", "week")
    if group_by not in ("day", "week", "month"):
        group_by = "week"

    q = Booking.query
    if regime in ("presencial", "online"):
        q = q.filter(db.func.lower(Booking.regime) == regime)
    if local:
        q = q.filter(Booking.local_consulta == local)
    if date_from:
        q = q.filter(Booking.slot_date >= _date.fromisoformat(date_from))
    if date_to:
        q = q.filter(Booking.slot_date <= _date.fromisoformat(date_to))

    rows = [{
        "regime": b.regime, "price": b.price, "status": b.status,
        "local_consulta": b.local_consulta, "slot_date": b.slot_date,
    } for b in q.all()]

    result = stats_mod.summarize(rows)
    result["series"] = stats_mod.build_series(rows, group_by)
    result["group_by"] = group_by
    return jsonify(result)


@admin_bp.route("/locations")
@auth.require_admin
def locations_view():
    rows = (db.session.query(Booking.local_consulta)
            .filter(Booking.local_consulta.isnot(None))
            .distinct().all())
    locs = sorted({r[0] for r in rows if r[0]})
    return jsonify({"locations": locs})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_admin_stats.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/admin_routes.py backend/tests/test_admin_stats.py
git commit -m "feat: admin stats and locations routes"
```

---

### Task 7: Edit booking (DB + calendar sync + client email)

**Files:**
- Modify: `backend/calendar_service.py` (extract `_event_body`, add `update_event`)
- Modify: `backend/email_service.py` (add `send_booking_updated_client`)
- Modify: `backend/admin_routes.py` (add `PUT /bookings/<ref>`)
- Test: `backend/tests/test_admin_edit.py`

- [ ] **Step 1: Add `update_event` to calendar_service**

In `backend/calendar_service.py`, refactor `create_event` to share a body builder. Replace the body dict inside `create_event` by adding this helper above `create_event`:
```python
def _event_body(booking):
    tz = pytz.timezone(TIMEZONE)
    start_dt = tz.localize(datetime.combine(booking.slot_date, booking.slot_time))
    end_dt = start_dt + timedelta(minutes=int(booking.duration_minutes))
    regime_info = booking.regime
    if booking.local_consulta:
        regime_info = f"{booking.regime} — {booking.local_consulta}"
    return {
        "summary": f"[IB] {booking.nome} — {booking.tipo_consulta}",
        "description": (
            f"Referência: {booking.reference}\n"
            f"Email: {booking.email}\n"
            f"Contacto: {booking.contacto}\n"
            f"Regime: {regime_info}\n"
            f"Preço: {float(booking.price):.0f}€\n"
            f"Duração: {booking.duration_minutes} min\n\n"
            f"Contexto: {booking.contexto or 'Sem contexto adicional'}"
        ),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
    }
```

Then set `create_event` to use it:
```python
def create_event(booking):
    service = _get_service()
    if not service:
        return None
    try:
        result = service.events().insert(calendarId=CALENDAR_ID, body=_event_body(booking)).execute()
        return result.get("id")
    except Exception as e:
        print(f"[Calendar] Create event error: {e}")
        return None
```

And add `update_event` after `delete_event`:
```python
def update_event(event_id, booking):
    """Patch an existing event to match the booking. Falls back to creating
    a new event if the old one is missing. Returns the (possibly new) event id."""
    service = _get_service()
    if not service:
        return event_id
    if not event_id:
        return create_event(booking)
    try:
        result = service.events().update(
            calendarId=CALENDAR_ID, eventId=event_id, body=_event_body(booking)
        ).execute()
        return result.get("id")
    except Exception as e:
        print(f"[Calendar] Update event error: {e}; recreating.")
        return create_event(booking)
```

- [ ] **Step 2: Add the client "updated" email**

In `backend/email_service.py`, add after `send_booking_confirmation`:
```python
def send_booking_updated_client(booking):
    html = _base_style() + f"""
    <h2 style="font-family:Georgia,serif;font-weight:400;color:#2C1A1A;">Consulta Atualizada</h2>
    <p>Olá <strong>{booking.nome}</strong>,</p>
    <p>Os detalhes da tua consulta foram atualizados. Confirma abaixo os novos dados.</p>
    {_booking_detail_block(booking)}
    <p>Se algo não estiver correto, responde a este email ou contacta-nos.</p>
    <p>Com os melhores cumprimentos,<br><strong>Inês Bandarra</strong></p>
    </div>
    """
    _send(booking.email, f"Consulta Atualizada — {booking.reference}", html)
```

- [ ] **Step 3: Write failing tests**

Create `backend/tests/test_admin_edit.py`:
```python
from conftest import TEST_PASSWORD, make_booking
import admin_routes


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


def test_edit_updates_fields_and_notifies(client, app, monkeypatch):
    calls = {"update": 0, "email": 0}
    monkeypatch.setattr(admin_routes.calendar_service, "update_event",
                        lambda eid, b: eid or "evt-new")
    monkeypatch.setattr(admin_routes.email_service, "send_booking_updated_client",
                        lambda b: calls.__setitem__("email", calls["email"] + 1))
    with app.app_context():
        make_booking(reference="IB-A", nome="Old Name", price=50, google_event_id="evt1")
    _auth(client)
    r = client.put("/api/admin/bookings/IB-A", json={"nome": "New Name", "price": 55})
    assert r.status_code == 200
    body = r.get_json()["booking"]
    assert body["nome"] == "New Name"
    assert body["price"] == 55.0
    assert calls["email"] == 1


def test_edit_missing_booking(client, app):
    _auth(client)
    r = client.put("/api/admin/bookings/IB-NOPE", json={"nome": "x"})
    assert r.status_code == 404
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_admin_edit.py -q`
Expected: FAIL — route missing (404 for the edit) / attribute errors.

- [ ] **Step 5: Implement the edit route**

In `backend/admin_routes.py`, add imports near the top:
```python
import calendar_service
import email_service
```

Add the route:
```python
EDITABLE_FIELDS = {
    "nome", "email", "contacto", "idade", "sujeito", "tipo_consulta",
    "regime", "local_consulta", "duration_minutes", "price", "contexto", "status",
}


@admin_bp.route("/bookings/<reference>", methods=["PUT"])
@auth.require_admin
def edit_booking(reference):
    from datetime import date as d, time as t
    booking = Booking.query.filter_by(reference=reference.upper()).first()
    if not booking:
        return jsonify({"error": "not_found"}), 404

    data = request.get_json(force=True) or {}
    for field in EDITABLE_FIELDS:
        if field in data and data[field] is not None:
            setattr(booking, field, data[field])
    if "slot_date" in data and data["slot_date"]:
        booking.slot_date = d.fromisoformat(data["slot_date"])
    if "slot_time" in data and data["slot_time"]:
        hh, mm = str(data["slot_time"]).split(":")
        booking.slot_time = t(int(hh), int(mm))
    if booking.regime and booking.regime.lower() == "online":
        booking.local_consulta = None

    db.session.commit()

    partial = []
    try:
        booking.google_event_id = calendar_service.update_event(booking.google_event_id, booking)
        db.session.commit()
    except Exception as e:
        partial.append(f"calendar: {e}")
    try:
        email_service.send_booking_updated_client(booking)
    except Exception as e:
        partial.append(f"email: {e}")

    return jsonify({"booking": _booking_admin_dict(booking), "partial_failures": partial})
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_admin_edit.py -q`
Expected: PASS (2 passed).

- [ ] **Step 7: Commit**

```bash
git add backend/calendar_service.py backend/email_service.py backend/admin_routes.py backend/tests/test_admin_edit.py
git commit -m "feat: admin edit booking with calendar sync and client email"
```

---

### Task 8: Cancel and hard-delete

**Files:**
- Modify: `backend/admin_routes.py` (add cancel + delete)
- Test: `backend/tests/test_admin_cancel_delete.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_admin_cancel_delete.py`:
```python
from conftest import TEST_PASSWORD, make_booking
from models import Booking
import admin_routes


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


def test_cancel_sets_status_and_emails(client, app, monkeypatch):
    seen = {"client": 0, "nutri": 0, "deleted": 0}
    monkeypatch.setattr(admin_routes.calendar_service, "delete_event",
                        lambda eid: seen.__setitem__("deleted", seen["deleted"] + 1))
    monkeypatch.setattr(admin_routes.email_service, "send_booking_cancelled_client",
                        lambda b: seen.__setitem__("client", 1))
    monkeypatch.setattr(admin_routes.email_service, "send_nutritionist_cancellation",
                        lambda b: seen.__setitem__("nutri", 1))
    with app.app_context():
        make_booking(reference="IB-A", google_event_id="evt1")
    _auth(client)
    r = client.post("/api/admin/bookings/IB-A/cancel")
    assert r.status_code == 200
    assert seen == {"client": 1, "nutri": 1, "deleted": 1}
    with app.app_context():
        assert Booking.query.filter_by(reference="IB-A").first().status == "cancelado"


def test_hard_delete_removes_row(client, app, monkeypatch):
    monkeypatch.setattr(admin_routes.calendar_service, "delete_event", lambda eid: None)
    with app.app_context():
        make_booking(reference="IB-A", google_event_id="evt1")
    _auth(client)
    r = client.delete("/api/admin/bookings/IB-A")
    assert r.status_code == 200
    with app.app_context():
        assert Booking.query.filter_by(reference="IB-A").first() is None


def test_delete_missing(client):
    _auth(client)
    assert client.delete("/api/admin/bookings/IB-NOPE").status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_admin_cancel_delete.py -q`
Expected: FAIL — routes missing.

- [ ] **Step 3: Implement cancel + delete**

In `backend/admin_routes.py`, add:
```python
@admin_bp.route("/bookings/<reference>/cancel", methods=["POST"])
@auth.require_admin
def cancel_booking_admin(reference):
    from datetime import datetime
    booking = Booking.query.filter_by(reference=reference.upper()).first()
    if not booking:
        return jsonify({"error": "not_found"}), 404
    if booking.status == "cancelado":
        return jsonify({"error": "already_cancelled"}), 400
    booking.status = "cancelado"
    booking.updated_at = datetime.utcnow()
    db.session.commit()
    if booking.google_event_id:
        calendar_service.delete_event(booking.google_event_id)
    email_service.send_booking_cancelled_client(booking)
    email_service.send_nutritionist_cancellation(booking)
    return jsonify({"booking": _booking_admin_dict(booking)})


@admin_bp.route("/bookings/<reference>", methods=["DELETE"])
@auth.require_admin
def delete_booking_admin(reference):
    booking = Booking.query.filter_by(reference=reference.upper()).first()
    if not booking:
        return jsonify({"error": "not_found"}), 404
    if booking.google_event_id:
        calendar_service.delete_event(booking.google_event_id)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"ok": True})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_admin_cancel_delete.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS (all tasks' tests green).

- [ ] **Step 6: Commit**

```bash
git add backend/admin_routes.py backend/tests/test_admin_cancel_delete.py
git commit -m "feat: admin cancel and hard-delete routes"
```

---

# PHASE 2 — Frontend

> Verification uses the Claude Preview server against the running app. Start the backend (`cd backend && flask --app app run` with a local `.env` containing the admin config and `ADMIN_COOKIE_SECURE=false`) and the frontend (`cd website && npm run dev`). Log in with the password whose hash is in `.env`.

### Task 9: Admin API client + route + auth gating

**Files:**
- Create: `website/src/admin/adminApi.js`
- Create: `website/src/admin/AdminPage.jsx`
- Create: `website/src/admin/AdminLogin.jsx`
- Modify: `website/src/App.jsx`

- [ ] **Step 1: Create the API wrapper**

Create `website/src/admin/adminApi.js`:
```javascript
const BASE = '/api/admin';

async function req(path, options = {}) {
  const res = await fetch(BASE + path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (res.status === 401) throw new Error('unauthorized');
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || 'request_failed');
  return body;
}

export const adminApi = {
  session: () => req('/session'),
  login: (password) => req('/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => req('/logout', { method: 'POST' }),
  bookings: (params) => req('/bookings?' + new URLSearchParams(params).toString()),
  locations: () => req('/locations'),
  stats: (params) => req('/stats?' + new URLSearchParams(params).toString()),
  editBooking: (ref, data) => req(`/bookings/${ref}`, { method: 'PUT', body: JSON.stringify(data) }),
  cancelBooking: (ref) => req(`/bookings/${ref}/cancel`, { method: 'POST' }),
  deleteBooking: (ref) => req(`/bookings/${ref}`, { method: 'DELETE' }),
};
```

- [ ] **Step 2: Create the login screen**

Create `website/src/admin/AdminLogin.jsx`:
```javascript
import { useState } from 'react';
import { adminApi } from './adminApi';

export default function AdminLogin({ onSuccess }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try {
      await adminApi.login(password);
      onSuccess();
    } catch {
      setError('Palavra-passe incorreta.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-login">
      <form className="admin-login-card" onSubmit={submit}>
        <img src="/images/vermelho.png" alt="IB Nutrição" className="admin-login-logo" />
        <h1>Painel de Administração</h1>
        <p>Introduz a palavra-passe para continuar.</p>
        <input
          type="password" value={password} autoFocus
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Palavra-passe"
        />
        {error && <span className="admin-login-error">{error}</span>}
        <button type="submit" disabled={busy}>{busy ? 'A entrar…' : 'Entrar'}</button>
      </form>
    </div>
  );
}
```

- [ ] **Step 3: Create the page shell with auth gating**

Create `website/src/admin/AdminPage.jsx`:
```javascript
import { useEffect, useState } from 'react';
import { adminApi } from './adminApi';
import AdminLogin from './AdminLogin';
import AdminDashboard from './AdminDashboard';
import './admin.css';

export default function AdminPage() {
  const [state, setState] = useState('loading'); // loading | out | in

  const check = () => adminApi.session()
    .then((r) => setState(r.authenticated ? 'in' : 'out'))
    .catch(() => setState('out'));

  useEffect(() => { check(); }, []);

  if (state === 'loading') return <div className="admin-loading">A carregar…</div>;
  if (state === 'out') return <AdminLogin onSuccess={() => setState('in')} />;
  return <AdminDashboard onLogout={() => setState('out')} />;
}
```

- [ ] **Step 4: Add the route**

In `website/src/App.jsx`, add the import and route:
```javascript
import AdminPage from './admin/AdminPage';
```
Add inside `<Routes>`:
```javascript
<Route path="/admin" element={<AdminPage />} />
```

- [ ] **Step 5: Temporary dashboard stub to allow build**

Create `website/src/admin/AdminDashboard.jsx` (replaced fully in Task 10):
```javascript
export default function AdminDashboard({ onLogout }) {
  return <div style={{ padding: 40 }}><button onClick={onLogout}>Sair</button></div>;
}
```
Create an empty `website/src/admin/admin.css` (styled in Task 13).

- [ ] **Step 6: Verify build + login flow**

Run the app; open `/admin` in the Preview server. Expected: login card with logo; wrong password shows error; correct password reveals the stub with a "Sair" button; reload keeps you logged in (cookie persists).

- [ ] **Step 7: Commit**

```bash
git add website/src/admin/adminApi.js website/src/admin/AdminPage.jsx website/src/admin/AdminLogin.jsx website/src/admin/AdminDashboard.jsx website/src/admin/admin.css website/src/App.jsx
git commit -m "feat: admin route, API client, and login gating"
```

---

### Task 10: Dashboard shell (brand header + tabs)

**Files:**
- Modify: `website/src/admin/AdminDashboard.jsx`

- [ ] **Step 1: Implement the dashboard shell**

Replace `website/src/admin/AdminDashboard.jsx`:
```javascript
import { useState } from 'react';
import { adminApi } from './adminApi';
import BookingsTab from './BookingsTab';
import StatsTab from './StatsTab';

export default function AdminDashboard({ onLogout }) {
  const [tab, setTab] = useState('bookings');

  const logout = async () => {
    try { await adminApi.logout(); } finally { onLogout(); }
  };

  return (
    <div className="admin">
      <header className="admin-top">
        <div className="admin-brand">
          <img src="/images/vermelho.png" alt="IB Nutrição" />
          <div>
            <span className="admin-brand-name">IB Nutrição</span>
            <small>Painel de Administração</small>
          </div>
        </div>
        <button className="admin-logout" onClick={logout}>Terminar sessão</button>
      </header>

      <nav className="admin-tabs">
        <button className={tab === 'bookings' ? 'on' : ''} onClick={() => setTab('bookings')}>Marcações</button>
        <button className={tab === 'stats' ? 'on' : ''} onClick={() => setTab('stats')}>Estatísticas</button>
      </nav>

      {tab === 'bookings' ? <BookingsTab /> : <StatsTab />}
    </div>
  );
}
```

- [ ] **Step 2: Create minimal tab stubs so it builds**

Create `website/src/admin/BookingsTab.jsx`:
```javascript
export default function BookingsTab() { return <div>Marcações…</div>; }
```
Create `website/src/admin/StatsTab.jsx`:
```javascript
export default function StatsTab() { return <div>Estatísticas…</div>; }
```

- [ ] **Step 3: Verify**

Reload `/admin`. Expected: header with the red logo + wordmark + "Terminar sessão"; two tabs that switch between the two stub texts; logout returns to login.

- [ ] **Step 4: Commit**

```bash
git add website/src/admin/AdminDashboard.jsx website/src/admin/BookingsTab.jsx website/src/admin/StatsTab.jsx
git commit -m "feat: admin dashboard shell with brand header and tabs"
```

---

### Task 11: Bookings tab (filters + table + actions)

**Files:**
- Modify: `website/src/admin/BookingsTab.jsx`
- Create: `website/src/admin/EditBookingModal.jsx`

- [ ] **Step 1: Implement the bookings tab**

Replace `website/src/admin/BookingsTab.jsx`:
```javascript
import { useEffect, useState, useCallback } from 'react';
import { adminApi } from './adminApi';
import EditBookingModal from './EditBookingModal';

const REGIME_LABEL = { presencial: 'Presencial', online: 'Online' };

function fmtDate(iso) {
  const d = new Date(iso + 'T00:00:00');
  return d.toLocaleDateString('pt-PT', { day: 'numeric', month: 'short', year: 'numeric' });
}
function fmtDur(m) { return m === 90 ? '1h30' : '1h'; }

export default function BookingsTab() {
  const [filters, setFilters] = useState({ q: '', status: 'all', regime: 'all', local_consulta: '', date_from: '', date_to: '' });
  const [data, setData] = useState({ bookings: [], summary: {} });
  const [locations, setLocations] = useState([]);
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v && v !== 'all'));
    try { setData(await adminApi.bookings(params)); } finally { setLoading(false); }
  }, [filters]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { adminApi.locations().then((r) => setLocations(r.locations)).catch(() => {}); }, []);

  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));

  const cancel = async (ref) => {
    if (!confirm(`Cancelar a marcação ${ref}? O cliente será notificado.`)) return;
    await adminApi.cancelBooking(ref); load();
  };
  const remove = async (ref) => {
    if (!confirm(`Eliminar PERMANENTEMENTE a marcação ${ref}? Esta ação não pode ser revertida.`)) return;
    await adminApi.deleteBooking(ref); load();
  };

  return (
    <div className="tab">
      <div className="filters">
        <div className="fld grow"><label>Pesquisar</label>
          <input placeholder="Nome, email ou referência…" value={filters.q} onChange={set('q')} /></div>
        <div className="fld"><label>Estado</label>
          <select value={filters.status} onChange={set('status')}>
            <option value="all">Todos</option><option value="confirmado">Confirmado</option><option value="cancelado">Cancelado</option>
          </select></div>
        <div className="fld"><label>Regime</label>
          <select value={filters.regime} onChange={set('regime')}>
            <option value="all">Todos</option><option value="presencial">Presencial</option><option value="online">Online</option>
          </select></div>
        <div className="fld"><label>Local</label>
          <select value={filters.local_consulta} onChange={set('local_consulta')}>
            <option value="">Todos</option>{locations.map((l) => <option key={l} value={l}>{l}</option>)}
          </select></div>
        <div className="fld"><label>De</label><input type="date" value={filters.date_from} onChange={set('date_from')} /></div>
        <div className="fld"><label>Até</label><input type="date" value={filters.date_to} onChange={set('date_to')} /></div>
      </div>

      <div className="table-wrap">
        <table className="adm-table">
          <thead><tr>
            <th>Ref.</th><th>Data / Hora</th><th>Cliente</th><th>Consulta</th><th>Regime / Local</th><th>Preço</th><th>Estado</th><th>Ações</th>
          </tr></thead>
          <tbody>
            {data.bookings.map((b) => (
              <tr key={b.reference} className={b.status === 'cancelado' ? 'row-canc' : ''}>
                <td data-label="Ref." className="ref">{b.reference}</td>
                <td data-label="Data">{fmtDate(b.slot_date)}<div className="sub">{b.slot_time} · {fmtDur(b.duration_minutes)}</div></td>
                <td data-label="Cliente">{b.nome}<div className="sub">{b.email} · {b.contacto}</div></td>
                <td data-label="Consulta">{b.tipo_consulta}<div className="sub">{b.sujeito} · {b.idade}</div></td>
                <td data-label="Regime"><span className={`pill ${b.regime === 'online' ? 'onl' : 'pres'}`}>{REGIME_LABEL[b.regime] || b.regime}</span>{b.local_consulta && <div className="sub">{b.local_consulta}</div>}</td>
                <td data-label="Preço">{Number(b.price).toFixed(0)}€</td>
                <td data-label="Estado"><span className={`pill ${b.status === 'cancelado' ? 'canc' : 'ok'}`}>{b.status === 'cancelado' ? 'Cancelado' : 'Confirmado'}</span></td>
                <td data-label="Ações"><div className="acts">
                  {b.status !== 'cancelado' && <button className="ic" title="Editar" onClick={() => setEditing(b)}>✎</button>}
                  {b.status !== 'cancelado' && <button className="ic" title="Cancelar" onClick={() => cancel(b.reference)}>⊘</button>}
                  <button className="ic" title="Eliminar" onClick={() => remove(b.reference)}>🗑</button>
                </div></td>
              </tr>
            ))}
            {!loading && data.bookings.length === 0 && <tr><td colSpan="8" className="empty">Sem marcações para estes filtros.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="adm-foot">
        <span>{data.summary.count || 0} marcações · {data.summary.confirmed_count || 0} confirmadas</span>
        <span>Faturado no período: <strong>{Number(data.summary.faturado || 0).toFixed(0)}€</strong></span>
      </div>

      {editing && <EditBookingModal booking={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
    </div>
  );
}
```

- [ ] **Step 2: Implement the edit modal**

Create `website/src/admin/EditBookingModal.jsx`:
```javascript
import { useState } from 'react';
import { adminApi } from './adminApi';

const FIELDS = [
  ['nome', 'Nome', 'text'], ['email', 'Email', 'email'], ['contacto', 'Contacto', 'text'],
  ['idade', 'Idade', 'number'], ['sujeito', 'Sujeito', 'text'], ['tipo_consulta', 'Tipo de consulta', 'text'],
  ['slot_date', 'Data', 'date'], ['slot_time', 'Hora', 'time'], ['price', 'Preço (€)', 'number'],
];

export default function EditBookingModal({ booking, onClose, onSaved }) {
  const [form, setForm] = useState({ ...booking });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = async () => {
    setBusy(true); setErr('');
    try {
      await adminApi.editBooking(booking.reference, {
        ...form,
        idade: Number(form.idade), price: Number(form.price),
        duration_minutes: Number(form.duration_minutes),
      });
      onSaved();
    } catch { setErr('Não foi possível guardar.'); setBusy(false); }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Editar {booking.reference}</h3>
        <div className="modal-grid">
          {FIELDS.map(([k, label, type]) => (
            <div className="fld" key={k}><label>{label}</label>
              <input type={type} value={form[k] ?? ''} onChange={set(k)} /></div>
          ))}
          <div className="fld"><label>Regime</label>
            <select value={form.regime} onChange={set('regime')}>
              <option value="presencial">Presencial</option><option value="online">Online</option>
            </select></div>
          <div className="fld"><label>Duração</label>
            <select value={form.duration_minutes} onChange={set('duration_minutes')}>
              <option value={60}>1h</option><option value={90}>1h30</option>
            </select></div>
          {form.regime === 'presencial' && (
            <div className="fld"><label>Local</label>
              <input value={form.local_consulta ?? ''} onChange={set('local_consulta')} /></div>
          )}
          <div className="fld"><label>Estado</label>
            <select value={form.status} onChange={set('status')}>
              <option value="confirmado">Confirmado</option><option value="cancelado">Cancelado</option>
            </select></div>
        </div>
        {err && <p className="modal-err">{err}</p>}
        <p className="modal-note">Ao guardar, o Google Calendar é atualizado e o cliente recebe um email.</p>
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn-red" onClick={save} disabled={busy}>{busy ? 'A guardar…' : 'Guardar'}</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify**

Reload `/admin` → Marcações. Expected: filters query the API and update the table; edit opens the modal, saving updates the row; cancel greys the row; delete removes it. (With an empty DB, seed a booking via the public booking flow first.)

- [ ] **Step 4: Commit**

```bash
git add website/src/admin/BookingsTab.jsx website/src/admin/EditBookingModal.jsx
git commit -m "feat: admin bookings tab with filters, edit, cancel, delete"
```

---

### Task 12: Stats tab (KPIs + chart + breakdowns)

**Files:**
- Modify: `website/src/admin/StatsTab.jsx`
- Create: `website/src/admin/MiniBarChart.jsx`

- [ ] **Step 1: Implement the chart component**

Create `website/src/admin/MiniBarChart.jsx`:
```javascript
import { useState } from 'react';

export default function MiniBarChart({ series }) {
  const [metric, setMetric] = useState('lucro'); // 'lucro' | 'count'
  const key = metric === 'lucro' ? 'lucro_liquido' : 'count';
  const max = Math.max(1, ...series.map((s) => s[key]));

  return (
    <div className="card">
      <div className="chart-head">
        <h3>Evolução</h3>
        <div className="metric-seg">
          <button className={metric === 'count' ? 'on' : ''} onClick={() => setMetric('count')}>Nº consultas</button>
          <button className={metric === 'lucro' ? 'on' : ''} onClick={() => setMetric('lucro')}>Lucro líquido</button>
        </div>
      </div>
      <div className="chart-sub">a mostrar {metric === 'lucro' ? 'lucro líquido (€)' : 'nº de consultas'} por período</div>
      <div className="chart">
        {series.length === 0 && <p className="empty">Sem dados no período.</p>}
        {series.map((s) => (
          <div className="bar-col" key={s.period}>
            <div className="bar" style={{ height: `${(s[key] / max) * 100}%` }}>
              <b>{metric === 'lucro' ? `${Math.round(s.lucro_liquido)}€` : s.count}</b>
            </div>
            <small>{s.period.replace('2026-', '').replace('W', 'S')}</small>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Implement the stats tab**

Replace `website/src/admin/StatsTab.jsx`:
```javascript
import { useEffect, useState, useCallback } from 'react';
import { adminApi } from './adminApi';
import MiniBarChart from './MiniBarChart';

const eur = (n) => `${Number(n || 0).toLocaleString('pt-PT', { maximumFractionDigits: 0 })}€`;

export default function StatsTab() {
  const [filters, setFilters] = useState({ date_from: '', date_to: '', regime: 'all', local_consulta: '', group_by: 'week' });
  const [locations, setLocations] = useState([]);
  const [data, setData] = useState(null);

  const load = useCallback(async () => {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v && v !== 'all'));
    if (!params.group_by) params.group_by = filters.group_by;
    setData(await adminApi.stats({ ...params, group_by: filters.group_by }));
  }, [filters]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { adminApi.locations().then((r) => setLocations(r.locations)).catch(() => {}); }, []);

  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));
  if (!data) return <div className="tab">A carregar…</div>;

  return (
    <div className="tab">
      <div className="filters">
        <div className="fld"><label>De</label><input type="date" value={filters.date_from} onChange={set('date_from')} /></div>
        <div className="fld"><label>Até</label><input type="date" value={filters.date_to} onChange={set('date_to')} /></div>
        <div className="fld"><label>Regime</label>
          <select value={filters.regime} onChange={set('regime')}>
            <option value="all">Todos</option><option value="presencial">Presencial</option><option value="online">Online</option>
          </select></div>
        <div className="fld"><label>Local</label>
          <select value={filters.local_consulta} onChange={set('local_consulta')}>
            <option value="">Todos</option>{locations.map((l) => <option key={l} value={l}>{l}</option>)}
          </select></div>
        <div className="fld"><label>Agrupar por</label>
          <div className="seg">
            {['day', 'week', 'month'].map((g) => (
              <button key={g} className={filters.group_by === g ? 'on' : ''} onClick={() => setFilters((f) => ({ ...f, group_by: g }))}>
                {g === 'day' ? 'Dia' : g === 'week' ? 'Semana' : 'Mês'}
              </button>
            ))}
          </div></div>
      </div>

      <div className="kpis">
        <div className="kpi"><div className="lab">Marcações</div><div className="val">{data.count}</div><div className="delta">confirmadas</div></div>
        <div className="kpi"><div className="lab">Faturado</div><div className="val">{eur(data.faturado)}</div><div className="delta">valor cobrado</div></div>
        <div className="kpi hi"><div className="lab">Lucro líquido</div><div className="val">{eur(data.lucro_liquido)}</div><div className="delta">70% pres · 100% online</div></div>
        <div className="kpi"><div className="lab">Canceladas</div><div className="val muted">{data.cancelled_count}</div><div className="delta">excluídas</div></div>
      </div>

      <div className="grid2">
        <MiniBarChart series={data.series} />
        <div className="card">
          <h3>Presencial vs Online</h3>
          {['presencial', 'online'].map((r) => (
            <div className="split-row" key={r}>
              <div className="split-line">
                <span className="nm"><span className={`dot ${r}`} />{r === 'presencial' ? 'Presencial' : 'Online'}</span>
                <span className="ct">{data.by_regime[r].count} · <strong>{eur(data.by_regime[r].lucro)}</strong> <span className="g">de {eur(data.by_regime[r].faturado)}</span></span>
              </div>
            </div>
          ))}
          <h3 style={{ marginTop: 22 }}>Por local <span>lucro líquido</span></h3>
          {data.by_location.length === 0 && <p className="empty">Sem presenciais no período.</p>}
          {data.by_location.map((l) => (
            <div className="loc" key={l.local_consulta}><span>{l.local_consulta}</span><span><span className="r">{eur(l.lucro)}</span> <span className="g">/ {l.count}</span></span></div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify**

Reload `/admin` → Estatísticas. Expected: KPIs reflect seeded data; chart toggle switches between counts and profit; changing Dia/Semana/Mês re-buckets; regime/local/date filters update all numbers.

- [ ] **Step 4: Commit**

```bash
git add website/src/admin/StatsTab.jsx website/src/admin/MiniBarChart.jsx
git commit -m "feat: admin stats tab with KPIs, chart toggle, breakdowns"
```

---

### Task 13: Styling + mobile responsive

**Files:**
- Modify: `website/src/admin/admin.css`

- [ ] **Step 1: Write the full stylesheet**

Replace `website/src/admin/admin.css` with the styling that reproduces the approved mockups (palette `--red #B94448`, cream `#FDF7F7`, blush gradients, white cards, Georgia headings, Jost body). Include:
- `.admin` page background + Jost font; `.admin-top`, `.admin-brand img{width:34px}`, `.admin-brand-name` (Georgia), `.admin-logout`.
- `.admin-tabs button` with `.on` = red fill.
- `.filters` grid; `.fld label/input/select`; `.seg` and `.metric-seg` segmented controls.
- `.adm-table` (header `#FBEFEF`, hover, `.ref`, `.sub`, `.pill.pres/.onl/.ok/.canc`, `.row-canc{opacity:.5}`, `.ic` action buttons), `.adm-foot`, `.empty`.
- `.kpis` 4-col grid, `.kpi`, `.kpi.hi` highlighted, `.val` Georgia, `.muted`.
- `.grid2` 1.6fr/1fr; `.card`, `.card h3` Georgia; `.chart`, `.bar-col`, `.bar` red gradient with `b` label; `.split-row`, `.dot.presencial{background:#3B7A57}`, `.dot.online{background:#3B5E8C}`, `.loc`, `.g` muted, `.r` red.
- `.admin-login` centered card with `.admin-login-logo{width:120px}`, input, `.admin-login-error`, submit button.
- `.modal-backdrop` (fixed, dim), `.modal` (white card, max-width 560px), `.modal-grid` 2-col, `.btn-red`/`.btn-ghost`, `.modal-note`, `.modal-err`.

**Responsive (`@media (max-width: 720px)`):**
```css
.filters { grid-template-columns: 1fr 1fr; }
.kpis { grid-template-columns: 1fr 1fr; }
.grid2 { grid-template-columns: 1fr; }
.modal-grid { grid-template-columns: 1fr; }
.admin { padding: 18px 12px; }
```
**Responsive table → cards (`@media (max-width: 640px)`):**
```css
.adm-table thead { display: none; }
.adm-table, .adm-table tbody, .adm-table tr, .adm-table td { display: block; width: 100%; }
.adm-table tr { border: 1px solid var(--line); border-radius: 12px; margin-bottom: 12px; background: #fff; padding: 6px 12px; }
.adm-table td { border: none; display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; }
.adm-table td::before { content: attr(data-label); color: var(--muted); font-size: .7rem; text-transform: uppercase; letter-spacing: .08em; }
.adm-table td.ref::before { content: ''; }
.acts { justify-content: flex-end; }
```
(The `data-label` attributes are already present on each `<td>` in `BookingsTab.jsx`.)

- [ ] **Step 2: Verify desktop + mobile**

In the Preview server: confirm desktop matches the mockups. Then use the responsive tool at ~375px width — filters collapse to 2 columns, KPIs go 2×2, the two-column stats stack, and the bookings table renders as stacked label/value cards with no horizontal scroll.

- [ ] **Step 3: Commit**

```bash
git add website/src/admin/admin.css
git commit -m "style: admin dashboard styling and mobile responsive layout"
```

---

# PHASE 3 — Deploy

### Task 14: Secrets, build, deploy, verify

**Files:** none (infra). Uses existing `deploy/` runbook.

- [ ] **Step 1: Generate secrets locally**

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('CHOOSE_A_STRONG_PASSWORD'))"
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Record the hash (`ADMIN_PASSWORD_HASH`) and the token secret (`ADMIN_TOKEN_SECRET`). Add both to `backend/.env` plus `ADMIN_COOKIE_SECURE=true`.

- [ ] **Step 2: Add ACA secrets + env to the backend app**

```bash
export AZURE_DEFAULTS_GROUP='rg-ibnutricao-prod'
az containerapp secret set -n ib-backend -g rg-ibnutricao-prod \
  --secrets admin-password-hash='<HASH>' admin-token-secret='<TOKEN_SECRET>'
az containerapp update -n ib-backend -g rg-ibnutricao-prod \
  --set-env-vars ADMIN_PASSWORD_HASH=secretref:admin-password-hash \
                 ADMIN_TOKEN_SECRET=secretref:admin-token-secret \
                 ADMIN_COOKIE_SECURE=true
```

- [ ] **Step 3: Build + push both images**

```bash
az acr login --name acribnutricao --resource-group rg-ibnutricao-prod
cd backend  && docker build -t acribnutricao.azurecr.io/ib-backend:v2 .  && docker push acribnutricao.azurecr.io/ib-backend:v2
cd ../website && docker build -t acribnutricao.azurecr.io/ib-frontend:v3 . && docker push acribnutricao.azurecr.io/ib-frontend:v3
```

- [ ] **Step 4: Roll both revisions**

```bash
az containerapp update -n ib-backend  -g rg-ibnutricao-prod --image acribnutricao.azurecr.io/ib-backend:v2
az containerapp update -n ib-frontend -g rg-ibnutricao-prod --image acribnutricao.azurecr.io/ib-frontend:v3
```

- [ ] **Step 5: Verify live**

- Open `https://<frontend>/admin` → login with the chosen password.
- In devtools, confirm the `admin_token` cookie is `HttpOnly` + `Secure`.
- Create a booking via the public flow, confirm it appears in Marcações; edit it (check the client email + calendar update); cancel one; hard-delete one.
- Open Estatísticas; confirm counts, faturado, lucro líquido (70/100 split), chart toggle, and per-location breakdown.
- Confirm a notification email shows the brand logo at the top.

- [ ] **Step 6: Commit any deploy-doc updates**

Update `deploy/README.md` with the new secrets and the `/admin` URL, then:
```bash
git add deploy/README.md
git commit -m "docs: admin secrets and URL in deploy runbook"
```

---

## Self-review notes

- **Spec coverage:** auth (Tasks 2–3), bookings list/filters (5), edit+calendar+email (7), cancel+hard-delete (8), stats with 70/100 net rule (4,6,12), chart count/profit toggle (12), brand icon in header+login (9,10), email logo (already done), mobile responsive (13), deploy+secrets (14). All spec sections map to a task.
- **Type consistency:** API method names in `adminApi.js` match the routes; stats JSON keys (`lucro_liquido`, `by_regime`, `by_location`, `series`, `count`, `faturado`, `cancelled_count`) are produced in `stats.py`/`stats_view` and consumed identically in `StatsTab.jsx`/`MiniBarChart.jsx`. Booking dict adds `idade`/`duration_minutes`/`updated_at` (`_booking_admin_dict`) which the table and modal read.
- **No placeholders:** the only intentional stub (`list_bookings` in Task 3) is explicitly replaced with full code in Task 5; frontend stubs in Tasks 9–10 are replaced in Tasks 10–12.
```
