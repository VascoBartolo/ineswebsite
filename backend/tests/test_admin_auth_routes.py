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
