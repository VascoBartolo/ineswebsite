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
