from conftest import TEST_PASSWORD, make_booking
import admin_routes
from models import Booking


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


def _payload(**overrides):
    data = dict(
        nome="Nova Cliente", email="Nova@Teste.PT", contacto="960111222",
        idade="34", sujeito="Adulto", tipo_consulta="Seguimento",
        regime="presencial", local_consulta="Clínica Manus",
        slot_date="2026-07-16", slot_time="17:00",
        duration_minutes=60, price=55,
    )
    data.update(overrides)
    return data


def _silence(monkeypatch, calls):
    monkeypatch.setattr(admin_routes.calendar_service, "update_event",
                        lambda eid, b: eid or "evt-new")
    for name in ("send_booking_confirmed_client", "send_booking_received_client"):
        monkeypatch.setattr(admin_routes.email_service, name,
                            lambda b, n=name: calls.__setitem__(n, calls.get(n, 0) + 1))


def test_create_requires_auth(client):
    r = client.post("/api/admin/bookings", json=_payload())
    assert r.status_code == 401


def test_create_persists_and_confirms_by_default(client, app, monkeypatch):
    calls = {}
    _silence(monkeypatch, calls)
    _auth(client)
    r = client.post("/api/admin/bookings", json=_payload(notify=True))
    assert r.status_code == 201
    body = r.get_json()["booking"]
    assert body["status"] == "confirmado"
    assert body["reference"].startswith("IB-")
    assert body["email"] == "nova@teste.pt"        # normalised
    assert body["local_consulta"] == "Clínica Manus"
    assert calls.get("send_booking_confirmed_client") == 1
    with app.app_context():
        assert Booking.query.filter_by(reference=body["reference"]).first() is not None


def test_create_without_notify_sends_no_email(client, app, monkeypatch):
    calls = {}
    _silence(monkeypatch, calls)
    _auth(client)
    r = client.post("/api/admin/bookings", json=_payload(notify=False))
    assert r.status_code == 201
    assert calls == {}


def test_create_sends_no_email_unless_asked(client, app, monkeypatch):
    """Omitting `notify` must stay silent: creating a booking is not on its own a
    reason to mail the client."""
    calls = {}
    _silence(monkeypatch, calls)
    _auth(client)
    payload = _payload()
    assert "notify" not in payload
    r = client.post("/api/admin/bookings", json=payload)
    assert r.status_code == 201
    assert calls == {}


def test_create_reports_missing_fields(client, app):
    _auth(client)
    payload = _payload()
    del payload["nome"]
    payload["slot_time"] = ""
    r = client.post("/api/admin/bookings", json=payload)
    assert r.status_code == 400
    body = r.get_json()
    assert body["error"] == "missing_fields"
    assert set(body["fields"]) == {"nome", "slot_time"}


def test_create_accepts_zero_price(client, app, monkeypatch):
    """A free consultation is a real case; 0 must not read as a missing field."""
    _silence(monkeypatch, {})
    _auth(client)
    r = client.post("/api/admin/bookings", json=_payload(price=0, notify=False))
    assert r.status_code == 201
    assert r.get_json()["booking"]["price"] == 0.0


def test_create_online_drops_local_consulta(client, app, monkeypatch):
    _silence(monkeypatch, {})
    _auth(client)
    r = client.post("/api/admin/bookings",
                    json=_payload(regime="online", local_consulta="Clínica Manus", notify=False))
    assert r.status_code == 201
    assert r.get_json()["booking"]["local_consulta"] is None


def test_create_rejects_bad_status_and_bad_slot(client, app):
    _auth(client)
    assert client.post("/api/admin/bookings",
                       json=_payload(status="inventado")).status_code == 400
    assert client.post("/api/admin/bookings",
                       json=_payload(slot_date="16-07-2026")).status_code == 400


def test_create_ignores_availability(client, app, monkeypatch):
    """The slot is already taken and the date is a feriado — she can still book it."""
    calls = {}
    _silence(monkeypatch, calls)
    with app.app_context():
        make_booking(reference="IB-TAKEN", slot_date=__import__("datetime").date(2026, 12, 25),
                     slot_time=__import__("datetime").time(17, 0))
    _auth(client)
    r = client.post("/api/admin/bookings",
                    json=_payload(slot_date="2026-12-25", slot_time="17:00", notify=False))
    assert r.status_code == 201


def test_create_references_are_unique(client, app, monkeypatch):
    _silence(monkeypatch, {})
    _auth(client)
    refs = set()
    for _ in range(5):
        r = client.post("/api/admin/bookings", json=_payload(notify=False))
        refs.add(r.get_json()["booking"]["reference"])
    assert len(refs) == 5


def test_create_records_first_consultation(client, app, monkeypatch):
    _silence(monkeypatch, {})
    _auth(client)
    r = client.post("/api/admin/bookings", json=_payload(is_first=True, notify=False))
    assert r.get_json()["booking"]["is_first"] is True


def test_create_records_follow_up(client, app, monkeypatch):
    _silence(monkeypatch, {})
    _auth(client)
    r = client.post("/api/admin/bookings", json=_payload(is_first=False, notify=False))
    assert r.get_json()["booking"]["is_first"] is False


def test_blank_is_first_stays_unrecorded(client, app, monkeypatch):
    """Blank must stay NULL: "not recorded" is not the same fact as "seguimento"."""
    _silence(monkeypatch, {})
    _auth(client)
    for blank in ("", None):
        r = client.post("/api/admin/bookings", json=_payload(is_first=blank, notify=False))
        assert r.status_code == 201
        assert r.get_json()["booking"]["is_first"] is None
    # omitted entirely
    p = _payload(notify=False)
    assert "is_first" not in p
    assert client.post("/api/admin/bookings", json=p).get_json()["booking"]["is_first"] is None
