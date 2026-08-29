from conftest import make_booking
from models import Booking
import auth
import booking_action_routes


def _sign(app, ref, action):
    with app.app_context():
        return auth.sign_booking_action(ref, action)


# ---- token layer ----

def test_booking_action_token_roundtrip(app):
    with app.app_context():
        token = auth.sign_booking_action("IB-A", "confirm")
        assert auth.verify_booking_action(token) == {"ref": "IB-A", "action": "confirm"}


def test_booking_action_token_tampered(app):
    with app.app_context():
        token = auth.sign_booking_action("IB-A", "confirm")
        assert auth.verify_booking_action(token + "x") is None


def test_booking_action_token_none(app):
    with app.app_context():
        assert auth.verify_booking_action("") is None
        assert auth.verify_booking_action(None) is None


def test_admin_token_not_accepted_as_booking_action(app):
    # Different salt -> an admin-session token must never validate as a booking action.
    with app.app_context():
        assert auth.verify_booking_action(auth.issue_token()) is None


# ---- GET landing page ----

def test_get_landing_shows_confirm_form(client, app):
    with app.app_context():
        make_booking(reference="IB-A")
    token = _sign(app, "IB-A", "confirm")
    r = client.get(f"/api/bookings/action?token={token}")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "<form" in body and "IB-A" in body
    assert "Confirmar Consulta" in body


def test_get_landing_invalid_token(client):
    r = client.get("/api/bookings/action?token=garbage")
    assert r.status_code == 400
    assert "inválida" in r.get_data(as_text=True)


def test_get_landing_cancelled_booking(client, app):
    with app.app_context():
        make_booking(reference="IB-A", status="cancelado")
    token = _sign(app, "IB-A", "confirm")
    r = client.get(f"/api/bookings/action?token={token}")
    assert r.status_code == 200
    assert "cancelada" in r.get_data(as_text=True)
    assert "<form" not in r.get_data(as_text=True)


# ---- POST execute ----

def test_post_confirm_sets_status_and_creates_event(client, app, monkeypatch):
    seen = {"confirmed": 0, "review": 0}
    monkeypatch.setattr(booking_action_routes.email_service,
                        "send_booking_confirmed_client",
                        lambda b: seen.__setitem__("confirmed", seen["confirmed"] + 1))
    monkeypatch.setattr(booking_action_routes.email_service,
                        "send_booking_review_client",
                        lambda b: seen.__setitem__("review", seen["review"] + 1))
    monkeypatch.setattr(booking_action_routes.calendar_service, "create_event", lambda b: "evt-new")
    with app.app_context():
        make_booking(reference="IB-A", status="pendente", google_event_id=None)
    token = _sign(app, "IB-A", "confirm")
    r = client.post("/api/bookings/action", data={"token": token})
    assert r.status_code == 200
    assert seen == {"confirmed": 1, "review": 0}
    with app.app_context():
        b = Booking.query.filter_by(reference="IB-A").first()
        assert b.status == "confirmado"
        assert b.google_event_id == "evt-new"  # calendar event created ONLY on approval


def test_post_revise_sets_status_and_emails(client, app, monkeypatch):
    seen = {"confirmed": 0, "review": 0}
    monkeypatch.setattr(booking_action_routes.email_service,
                        "send_booking_confirmed_client",
                        lambda b: seen.__setitem__("confirmed", seen["confirmed"] + 1))
    monkeypatch.setattr(booking_action_routes.email_service,
                        "send_booking_review_client",
                        lambda b: seen.__setitem__("review", seen["review"] + 1))
    with app.app_context():
        make_booking(reference="IB-B", status="pendente", google_event_id=None)
    token = _sign(app, "IB-B", "revise")
    r = client.post("/api/bookings/action", data={"token": token})
    assert r.status_code == 200
    assert seen == {"confirmed": 0, "review": 1}
    with app.app_context():
        assert Booking.query.filter_by(reference="IB-B").first().status == "revisao"


def test_post_revise_deletes_calendar_event(client, app, monkeypatch):
    """Rejecting a previously-confirmed booking removes its calendar event and frees the slot."""
    deleted = {"n": 0}
    monkeypatch.setattr(booking_action_routes.email_service, "send_booking_review_client", lambda b: None)
    monkeypatch.setattr(booking_action_routes.calendar_service, "delete_event",
                        lambda eid: deleted.__setitem__("n", deleted["n"] + 1))
    with app.app_context():
        make_booking(reference="IB-D", status="confirmado", google_event_id="evt-existing")
    token = _sign(app, "IB-D", "revise")
    r = client.post("/api/bookings/action", data={"token": token})
    assert r.status_code == 200
    assert deleted["n"] == 1
    with app.app_context():
        b = Booking.query.filter_by(reference="IB-D").first()
        assert b.status == "revisao"
        assert b.google_event_id is None


def test_post_confirm_idempotent(client, app, monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(booking_action_routes.email_service,
                        "send_booking_confirmed_client",
                        lambda b: calls.__setitem__("n", calls["n"] + 1))
    monkeypatch.setattr(booking_action_routes.calendar_service, "create_event", lambda b: "evt-x")
    with app.app_context():
        make_booking(reference="IB-A", status="pendente", google_event_id=None)
    token = _sign(app, "IB-A", "confirm")
    client.post("/api/bookings/action", data={"token": token})
    r2 = client.post("/api/bookings/action", data={"token": token})
    assert r2.status_code == 200
    assert calls["n"] == 1  # second click did not resend
    assert "Já confirmada" in r2.get_data(as_text=True)


def test_post_invalid_token(client):
    r = client.post("/api/bookings/action", data={"token": "nope"})
    assert r.status_code == 400


def test_post_cancelled_booking_blocked(client, app, monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(booking_action_routes.email_service,
                        "send_booking_confirmed_client",
                        lambda b: calls.__setitem__("n", calls["n"] + 1))
    with app.app_context():
        make_booking(reference="IB-C", status="cancelado")
    token = _sign(app, "IB-C", "confirm")
    r = client.post("/api/bookings/action", data={"token": token})
    assert r.status_code == 200
    assert calls["n"] == 0
    with app.app_context():
        assert Booking.query.filter_by(reference="IB-C").first().status == "cancelado"
