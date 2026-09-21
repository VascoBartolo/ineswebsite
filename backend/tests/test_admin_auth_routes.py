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


# ---- sliding session ----

def _token_issued_days_ago(app, monkeypatch, days):
    import time
    import auth
    from itsdangerous import TimestampSigner
    with monkeypatch.context() as m:
        m.setattr(TimestampSigner, "get_timestamp", lambda self: int(time.time() - days * 86400))
        with app.app_context():
            return auth.issue_token()


def test_session_lifetime_is_seven_days():
    import auth
    assert auth.TOKEN_MAX_AGE == 7 * 24 * 3600


def test_fresh_cookie_is_not_reissued(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})
    r = client.get("/api/admin/session")
    assert "Set-Cookie" not in r.headers


def test_day_old_cookie_is_renewed(client, app, monkeypatch):
    client.set_cookie("admin_token", _token_issued_days_ago(app, monkeypatch, 2), path="/api/admin")
    r = client.get("/api/admin/session")
    assert r.get_json()["authenticated"] is True
    assert "admin_token=" in r.headers.get("Set-Cookie", "")


def test_cookie_older_than_seven_days_is_rejected(client, app, monkeypatch):
    client.set_cookie("admin_token", _token_issued_days_ago(app, monkeypatch, 8), path="/api/admin")
    r = client.get("/api/admin/bookings")
    assert r.status_code == 401
    assert "Set-Cookie" not in r.headers


def test_logout_is_not_undone_by_renewal(client, app, monkeypatch):
    client.set_cookie("admin_token", _token_issued_days_ago(app, monkeypatch, 2), path="/api/admin")
    r = client.post("/api/admin/logout")
    cookies = r.headers.getlist("Set-Cookie")
    assert len(cookies) == 1 and "Max-Age=0" in cookies[0]
