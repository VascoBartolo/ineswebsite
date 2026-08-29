from datetime import date, timedelta

import app as app_module
from models import Booking


def _future_monday():
    """A Monday at least 3 days out, so the ≥24h-ahead slot filter keeps its slots."""
    d = date.today() + timedelta(days=3)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def _noop_emails(monkeypatch):
    monkeypatch.setattr(app_module.email_service, "send_booking_received_client", lambda b: None)
    monkeypatch.setattr(app_module.email_service, "send_nutritionist_new_booking", lambda b: None)


def _payload(**over):
    d = dict(
        sujeito="adulto", tipo_consulta="consulta na gravidez", regime="online",
        nome="Maria Teste", idade="34", email="maria@teste.pt", contacto="960000000",
        slot_date=_future_monday().isoformat(), slot_time="17:00", is_first=True,
    )
    d.update(over)
    return d


def test_create_booking_ok(client, app, monkeypatch):
    _noop_emails(monkeypatch)
    r = client.post("/api/bookings", json=_payload())
    assert r.status_code == 201, r.get_json()
    body = r.get_json()["booking"]
    assert body["idade"] == "34"
    assert body["status"] == "pendente"
    with app.app_context():
        assert Booking.query.filter_by(reference=body["reference"]).first() is not None


def test_create_booking_baby_age_in_months(client, monkeypatch):
    """The whole point of the change: a baby's age can be free text like '6 meses'."""
    _noop_emails(monkeypatch)
    r = client.post("/api/bookings", json=_payload(
        sujeito="bebé", tipo_consulta="introdução alimentar", idade="6 meses"))
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["booking"]["idade"] == "6 meses"


def test_create_booking_invalid_email(client, monkeypatch):
    _noop_emails(monkeypatch)
    r = client.post("/api/bookings", json=_payload(email="not-an-email"))
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_email"


def test_create_booking_field_too_long(client, monkeypatch):
    _noop_emails(monkeypatch)
    r = client.post("/api/bookings", json=_payload(nome="x" * 201))
    assert r.status_code == 400
    assert r.get_json()["error"] == "field_too_long"


def test_create_booking_missing_field(client):
    r = client.post("/api/bookings", json={"sujeito": "adulto"})
    assert r.status_code == 400


def test_create_booking_trims_whitespace(client, monkeypatch):
    _noop_emails(monkeypatch)
    r = client.post("/api/bookings", json=_payload(nome="  Maria Teste  "))
    assert r.status_code == 201
    assert r.get_json()["booking"]["nome"] == "Maria Teste"
