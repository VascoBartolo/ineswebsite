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


def test_public_booking_persists_is_first(client, app, monkeypatch):
    """The public form already sent is_first to price the consultation; it must
    now also be stored, or first-vs-follow-up is unrecoverable for online adults."""
    import app as app_mod
    from models import Booking
    monkeypatch.setattr(app_mod.calendar_service, "get_gcal_events", lambda d: [])
    monkeypatch.setattr(app_mod.calendar_service, "get_available_slots",
                        lambda d, dur, ev, loc=None: ["16:00"])
    monkeypatch.setattr(app_mod.email_service, "send_booking_received_client", lambda b: None)
    monkeypatch.setattr(app_mod.email_service, "send_nutritionist_new_booking", lambda b: None)
    payload = {
        "sujeito": "Adulto", "tipo_consulta": "Consulta na Gravidez", "regime": "online",
        "nome": "Teste", "idade": "30", "email": "t@e.pt", "contacto": "960000000",
        "slot_date": "2026-12-15", "slot_time": "16:00", "is_first": False,
    }
    r = client.post("/api/bookings", json=payload)
    assert r.status_code == 201
    with app.app_context():
        b = Booking.query.filter_by(reference=r.get_json()["booking"]["reference"]).first()
        assert b.is_first is False


def test_emails_are_complete_html_documents(app, monkeypatch):
    """Gmail's mobile apps mis-measure a bare fragment and cut the message off
    part-way down. Every message must be a full document with a viewport."""
    import email_service as es
    from models import Booking
    from datetime import date, time

    sent = []

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, *a): pass
        def sendmail(self, frm, to, raw): sent.append(raw)

    monkeypatch.setattr(es.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(es, "SMTP_USER", "u")
    monkeypatch.setattr(es, "SMTP_PASS", "p")

    b = Booking(
        reference="IB-DOC1", sujeito="Adulto", tipo_consulta="Seguimento", regime="online",
        nome="Teste", idade="30", email="t@e.pt", contacto="960000000",
        slot_date=date(2026, 12, 10), slot_time=time(17, 0),
        duration_minutes=60, price=50, status="cancelado",
    )
    with app.app_context():
        es.send_booking_cancelled_client(b)

    assert sent, "no message was sent"
    import email as email_mod
    msg = email_mod.message_from_string(sent[0])
    assert msg.get("Date"), "Date header is required by RFC 5322"
    assert msg.get("Message-ID"), "Message-ID keeps separate notifications distinct"

    body = msg.get_payload(0).get_payload(decode=True).decode()
    assert body.lstrip().startswith("<!DOCTYPE html>")
    for needed in ("<html", "<head>", "charset", "viewport", "<body", "</body></html>"):
        assert needed in body, f"missing {needed}"
    assert body.count("<html") == 1 and body.count("<body") == 1
