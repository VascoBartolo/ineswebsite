import logging
from datetime import date, time, timedelta

import pytest

from conftest import TEST_PASSWORD, make_booking
from models import Booking, LoginAttempt, db, utcnow
import auth
import email_service as es
import holidays_pt


# ---- security headers ----

def test_every_response_is_nosniff(client):
    assert client.get("/api/health").headers["X-Content-Type-Options"] == "nosniff"


def test_action_page_is_locked_down(client, app):
    with app.app_context():
        make_booking(reference="IB-H", status="pendente",
                     slot_date=date.today() + timedelta(days=30))
        token = auth.sign_booking_action("IB-H", "confirm")
    h = client.get(f"/api/bookings/action?token={token}").headers
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert "form-action 'self'" in h["Content-Security-Policy"]
    assert h["Referrer-Policy"] == "no-referrer"
    assert h["Cache-Control"] == "no-store"


# ---- CORS ----

def test_localhost_origin_not_allowed_by_default(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert "Access-Control-Allow-Origin" not in r.headers


# ---- login throttle shared across workers and replicas ----

@pytest.fixture
def no_delay(monkeypatch):
    monkeypatch.setattr(auth, "LOGIN_FAIL_DELAY", 0)


def _failures(app):
    with app.app_context():
        return LoginAttempt.query.count()


def test_failed_login_is_recorded_and_success_clears_it(client, app, no_delay):
    assert client.post("/api/admin/login", json={"password": "wrong"}).status_code == 401
    assert _failures(app) == 1
    assert client.post("/api/admin/login", json={"password": TEST_PASSWORD}).status_code == 200
    assert _failures(app) == 0


def test_login_locked_after_ten_recent_failures(client, app, no_delay):
    with app.app_context():
        db.session.add_all(LoginAttempt(ip="127.0.0.1") for _ in range(10))
        db.session.commit()
    r = client.post("/api/admin/login", json={"password": TEST_PASSWORD})
    assert r.status_code == 429
    assert "Set-Cookie" not in r.headers


def test_old_failures_do_not_lock(client, app, no_delay):
    with app.app_context():
        old = utcnow() - timedelta(minutes=20)
        db.session.add_all(LoginAttempt(ip="127.0.0.1", created_at=old) for _ in range(10))
        db.session.commit()
    assert client.post("/api/admin/login", json={"password": TEST_PASSWORD}).status_code == 200


def test_failures_older_than_a_day_are_pruned(client, app, no_delay):
    with app.app_context():
        db.session.add(LoginAttempt(ip="10.0.0.9", created_at=utcnow() - timedelta(days=2)))
        db.session.commit()
    client.post("/api/admin/login", json={"password": "wrong"})
    with app.app_context():
        assert LoginAttempt.query.filter_by(ip="10.0.0.9").count() == 0


# ---- email copy and transport ----

def _booking():
    return Booking(
        reference="IB-EM1", sujeito="adulto", tipo_consulta="consulta na gravidez", regime="online",
        nome="Teste", idade="30", email="t@e.pt", contacto="960000000",
        slot_date=date(2026, 12, 10), slot_time=time(17, 0),
        duration_minutes=60, price=50, status="confirmado",
    )


@pytest.mark.parametrize("send", [
    es.send_booking_received_client, es.send_booking_confirmed_client,
    es.send_booking_review_client, es.send_booking_updated_client,
])
def test_client_emails_use_formal_register_and_configured_contact(app, monkeypatch, send):
    sent = []
    monkeypatch.setattr(es, "_send", lambda to, subject, html, reply_to=None: sent.append(html))
    with app.app_context():
        send(_booking())
    html = sent[0]
    assert es.REPLY_TO in html
    for informal in ("tua consulta", "acede a", "Confirma abaixo"):
        assert informal not in html


def test_smtp_connection_has_a_timeout(app, monkeypatch):
    seen = {}

    class FakeSMTP:
        def __init__(self, *a, **k): seen.update(k)
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, *a): pass
        def sendmail(self, *a): pass

    monkeypatch.setattr(es.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(es, "SMTP_USER", "u")
    monkeypatch.setattr(es, "SMTP_PASS", "p")
    with app.app_context():
        es.send_booking_cancelled_client(_booking())
    assert seen.get("timeout") == 15


# ---- holiday table coverage ----

def test_holiday_table_covers_next_year():
    """Starts failing a year before the table runs out, while there is time to extend it."""
    assert date.today().year + 1 in holidays_pt.COVERED_YEARS


def test_uncovered_year_warns_once(caplog):
    with caplog.at_level(logging.WARNING, logger="ibnutricao.holidays"):
        holidays_pt.is_holiday(date(2099, 1, 1))
        holidays_pt.is_holiday(date(2099, 5, 1))
    assert len([r for r in caplog.records if "2099" in r.getMessage()]) == 1
