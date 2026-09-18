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


def test_edit_can_set_and_clear_is_first(client, app, monkeypatch):
    monkeypatch.setattr(admin_routes.calendar_service, "update_event", lambda eid, b: eid or "e")
    monkeypatch.setattr(admin_routes.email_service, "send_booking_updated_client", lambda b: None)
    with app.app_context():
        make_booking(reference="IB-F1")
    _auth(client)

    r = client.put("/api/admin/bookings/IB-F1", json={"is_first": True})
    assert r.get_json()["booking"]["is_first"] is True

    r = client.put("/api/admin/bookings/IB-F1", json={"is_first": False})
    assert r.get_json()["booking"]["is_first"] is False

    # Back to "not recorded" — EDITABLE_FIELDS' loop skips None, so this only
    # works because is_first is handled explicitly.
    r = client.put("/api/admin/bookings/IB-F1", json={"is_first": None})
    assert r.get_json()["booking"]["is_first"] is None


def test_edit_leaves_is_first_alone_when_absent(client, app, monkeypatch):
    monkeypatch.setattr(admin_routes.calendar_service, "update_event", lambda eid, b: eid or "e")
    monkeypatch.setattr(admin_routes.email_service, "send_booking_updated_client", lambda b: None)
    with app.app_context():
        make_booking(reference="IB-F2", is_first=True)
    _auth(client)
    r = client.put("/api/admin/bookings/IB-F2", json={"nome": "Outro Nome"})
    assert r.get_json()["booking"]["is_first"] is True
