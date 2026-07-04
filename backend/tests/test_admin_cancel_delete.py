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
