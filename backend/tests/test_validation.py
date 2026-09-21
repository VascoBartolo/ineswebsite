import re
from pathlib import Path

import pytest

from conftest import TEST_PASSWORD, make_booking
from models import Booking
from test_bookings import _noop_emails, _payload
from validation import CLINICS, SUJEITOS, TIPOS_CONSULTA
import admin_routes

JS_CONSTANTS = Path(__file__).resolve().parents[2] / "website/src/constants/booking.js"


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


# ---- enums stay in step with the booking form ----

@pytest.mark.skipif(not JS_CONSTANTS.exists(), reason="frontend sources not present")
def test_enums_match_frontend_constants():
    js = JS_CONSTANTS.read_text(encoding="utf-8")
    types_block = js.split("export const CONSULTATION_TYPES")[1].split("};")[0]
    js_types = {k: tuple(re.findall(r"id: '([^']+)'", body))
                for k, body in re.findall(r"(\w+): \[(.*?)\]", types_block, re.S)}
    assert js_types == TIPOS_CONSULTA
    assert set(js_types) == set(SUJEITOS)
    clinics_block = js.split("export const CLINICS")[1].split("];")[0]
    assert tuple(re.findall(r"'([^']+)'", clinics_block)) == CLINICS


# ---- public booking: only the options the form offers ----

@pytest.mark.parametrize("over, field", [
    ({"sujeito": "gato"}, "sujeito"),
    ({"regime": "telefone"}, "regime"),
    ({"tipo_consulta": "introdução alimentar"}, "tipo_consulta"),  # a bebé type for an adulto
    ({"regime": "presencial"}, "local_consulta"),
    ({"regime": "presencial", "local_consulta": "Clínica Inventada"}, "local_consulta"),
])
def test_public_booking_rejects_unknown_choices(client, monkeypatch, over, field):
    _noop_emails(monkeypatch)
    r = client.post("/api/bookings", json=_payload(**over))
    assert r.status_code == 400
    assert r.get_json() == {"error": "invalid_choice", "field": field}


def test_public_booking_canonicalises_choices(client, app, monkeypatch):
    _noop_emails(monkeypatch)
    r = client.post("/api/bookings", json=_payload(
        sujeito="Adulto", regime="PRESENCIAL", tipo_consulta="Consulta na Gravidez",
        local_consulta="clínica manus (angra do heroísmo)"))
    assert r.status_code == 201, r.get_json()
    b = r.get_json()["booking"]
    assert (b["sujeito"], b["regime"], b["tipo_consulta"], b["local_consulta"]) == (
        "adulto", "presencial", "consulta na gravidez", CLINICS[0])
    assert b["price"] == 55.0


def test_public_booking_requires_boolean_is_first(client, monkeypatch):
    _noop_emails(monkeypatch)
    r = client.post("/api/bookings", json=_payload(is_first="false"))
    assert r.status_code == 400
    assert r.get_json()["error"] == "invalid_is_first"


def test_public_booking_non_string_field_is_missing_not_500(client, monkeypatch):
    _noop_emails(monkeypatch)
    r = client.post("/api/bookings", json=_payload(nome=123))
    assert r.status_code == 400
    assert "nome" in r.get_json()["error"]


def test_booking_takes_postgres_advisory_lock(client, app, monkeypatch):
    """Tests run on SQLite, which skips the lock branch; force it so a broken
    lock call cannot hide until production."""
    from models import db
    _noop_emails(monkeypatch)
    locks = []
    real_execute = db.session.execute

    def execute(stmt, *a, **k):
        if "pg_advisory_xact_lock" in str(stmt):
            locks.append(a[0] if a else k)
            return None
        return real_execute(stmt, *a, **k)

    with app.app_context():
        monkeypatch.setattr(db.engine.dialect, "name", "postgresql")
    monkeypatch.setattr(db.session, "execute", execute)
    r = client.post("/api/bookings", json=_payload())
    assert r.status_code == 201, r.get_json()
    assert len(locks) == 1


# ---- malformed input is a 400, never a 500 ----

@pytest.mark.parametrize("method, url, kwargs", [
    ("post", "/api/bookings", {"json": [1, 2]}),
    ("post", "/api/contact", {"json": "texto"}),
    ("get", "/api/availability?date=2030-01-07&duration=abc", {}),
    ("get", "/api/availability?date=2030-01-07&duration=5000", {}),
    ("get", "/api/availability/month?year=99999&month=1", {}),
    ("get", "/api/availability/month?year=2030&month=13", {}),
    ("post", "/api/admin/login", {"json": ["x"]}),
])
def test_malformed_public_input_is_400(client, method, url, kwargs):
    r = getattr(client, method)(url, **kwargs)
    assert r.status_code == 400, r.get_data(as_text=True)


def test_cancel_with_null_email_is_not_500(client, app):
    with app.app_context():
        make_booking(reference="IB-N")
    r = client.put("/api/bookings/IB-N/cancel", json={"email": None})
    assert r.status_code == 404


def test_edit_request_message_capped(client, app, monkeypatch):
    monkeypatch.setattr(admin_routes.email_service, "send_nutritionist_edit_request", lambda b, m: None)
    with app.app_context():
        make_booking(reference="IB-M")
    r = client.put("/api/bookings/IB-M/edit-request",
                   json={"email": "cliente@teste.pt", "message": "x" * 2001})
    assert r.status_code == 400
    assert r.get_json()["field"] == "message"


def test_login_with_non_string_password_is_401(client):
    assert client.post("/api/admin/login", json={"password": 12345}).status_code == 401


@pytest.mark.parametrize("url", [
    "/api/admin/bookings?date_from=ontem",
    "/api/admin/bookings?page=abc",
    "/api/admin/stats?date_to=31-12-2026",
])
def test_malformed_admin_filters_are_400(client, url):
    _auth(client)
    assert client.get(url).status_code == 400


# ---- admin edit: validated before anything is written ----

@pytest.mark.parametrize("bad", [
    {"status": "inventado"},
    {"price": "abc"},
    {"price": -5},
    {"duration_minutes": 0},
    {"slot_date": "16-07-2026"},
    {"slot_time": "tarde"},
    {"email": "nope"},
    {"nome": ""},
    {"regime": "telefone"},
    {"nome": "x" * 201},
])
def test_admin_edit_rejects_bad_values_without_partial_write(client, app, monkeypatch, bad):
    monkeypatch.setattr(admin_routes.email_service, "send_booking_updated_client", lambda b: None)
    with app.app_context():
        make_booking(reference="IB-E", nome="Original")
    _auth(client)
    r = client.put("/api/admin/bookings/IB-E", json={"contacto": "911111111", **bad})
    assert r.status_code == 400, r.get_json()
    with app.app_context():
        b = Booking.query.filter_by(reference="IB-E").first()
        assert b.nome == "Original" and b.contacto == "960000000"


def test_admin_edit_keeps_legacy_free_text(client, app, monkeypatch):
    """Older rows hold types and clinics the form no longer offers; she can still save them."""
    monkeypatch.setattr(admin_routes.calendar_service, "update_event", lambda eid, b: eid)
    monkeypatch.setattr(admin_routes.email_service, "send_booking_updated_client", lambda b: None)
    with app.app_context():
        make_booking(reference="IB-L")
    _auth(client)
    r = client.put("/api/admin/bookings/IB-L", json={
        "sujeito": "Bebé", "tipo_consulta": "Pós-parto", "regime": "presencial",
        "local_consulta": "Clínica Manus", "price": "55", "duration_minutes": "90", "notify": False})
    assert r.status_code == 200, r.get_json()
    body = r.get_json()["booking"]
    assert body["price"] == 55.0 and body["duration_minutes"] == 90
