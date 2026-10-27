from datetime import date, datetime, time, timedelta
from types import SimpleNamespace as NS

import pytest
import stripe

import app as app_module
import email_service
import payments
from conftest import TEST_PASSWORD, make_booking
from models import Booking, db, utcnow
from test_bookings import _future_monday, _payload


@pytest.fixture
def fake_stripe(monkeypatch):
    """Records every Stripe call; nothing reaches the API."""
    calls = {"sessions": [], "captures": [], "cancels": [], "refunds": [], "emails": []}
    pi = {"status": "requires_capture", "amount_received": 0, "type": "card",
          "capture_before": int((datetime.now() + timedelta(days=7)).timestamp())}

    monkeypatch.setattr(payments.stripe, "api_key", "rk_test_x")

    def create(**kw):
        calls["sessions"].append(kw)
        return NS(id=f"cs_{len(calls['sessions'])}", url="https://checkout.stripe.com/x")

    def retrieve(pi_id, **kw):
        charge = NS(payment_method_details=NS(type=pi["type"], card=NS(capture_before=pi["capture_before"])))
        return NS(id=pi_id, status=pi["status"], amount_received=pi["amount_received"], latest_charge=charge)

    def capture(pi_id):
        calls["captures"].append(pi_id)
        return NS(amount_received=5000)

    monkeypatch.setattr(payments.stripe.checkout.Session, "create", create)
    monkeypatch.setattr(payments.stripe.PaymentIntent, "retrieve", retrieve)
    monkeypatch.setattr(payments.stripe.PaymentIntent, "capture", capture)
    monkeypatch.setattr(payments.stripe.PaymentIntent, "cancel", lambda pi_id: calls["cancels"].append(pi_id))
    monkeypatch.setattr(payments.stripe.Refund, "create", lambda **kw: calls["refunds"].append(kw))
    for name in ("send_booking_received_client", "send_nutritionist_new_booking",
                 "send_booking_cancelled_client", "send_nutritionist_cancellation",
                 "send_payment_expired_client", "send_refund_client", "send_booking_confirmed_client",
                 "send_booking_review_client", "send_booking_updated_client"):
        monkeypatch.setattr(email_service, name,
                            lambda *a, _n=name: calls["emails"].append((_n, a[0].reference)))
    calls["pi"] = pi
    return calls


def _event(monkeypatch, kind, obj):
    monkeypatch.setattr(stripe.Webhook, "construct_event",
                        lambda payload, sig, secret: NS(type=kind, data=NS(object=obj)))


def _online(**over):
    return _payload(regime="online", local_consulta=None, **over)


def _checkout(client):
    r = client.post("/api/payments/checkout", json=_online())
    assert r.status_code == 201, r.get_json()
    return r.get_json()["reference"]


def _complete(client, monkeypatch, ref):
    with client.application.app_context():
        session_id = Booking.query.filter_by(reference=ref).first().stripe_session_id
    _event(monkeypatch, "checkout.session.completed", NS(id=session_id, payment_intent="pi_1"))
    return client.post("/api/stripe/webhook", data=b"{}")


def _paid_booking(**kw):
    kw.setdefault("slot_date", date.today() + timedelta(days=10))
    return make_booking(payment_status="paid", stripe_payment_intent="pi_1",
                        amount_paid=50, **kw)


def _authorized(**kw):
    kw.setdefault("slot_date", date.today() + timedelta(days=10))
    kw.setdefault("status", "pendente")
    return make_booking(payment_status="authorized", stripe_payment_intent="pi_1", **kw)


def _soon():
    """A slot 5 hours ahead in practice time: inside the 24h notice period."""
    slot = app_module.calendar_service.now_azores() + timedelta(hours=5)
    return dict(slot_date=slot.date(), slot_time=time(slot.hour, 0))


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


# ---- booking entry points ----

def test_online_booking_without_payment_rejected(client):
    r = client.post("/api/bookings", json=_online())
    assert r.status_code == 400
    assert r.get_json()["error"] == "payment_required"


def test_presencial_never_touches_stripe(client, app, fake_stripe):
    r = client.post("/api/bookings", json=_payload())
    assert r.status_code == 201
    assert fake_stripe["sessions"] == []
    with app.app_context():
        b = Booking.query.one()
        assert b.payment_status is None and b.status == "pendente"
        assert b.terms_accepted_at is not None and b.terms_version


def test_terms_required(client, fake_stripe):
    for path, body in (("/api/bookings", _payload(terms_accepted=False)),
                       ("/api/payments/checkout", _online(terms_accepted=None))):
        r = client.post(path, json=body)
        assert r.status_code == 400 and r.get_json()["error"] == "terms_not_accepted"
    assert fake_stripe["sessions"] == []


def test_checkout_rejects_presencial(client, fake_stripe):
    r = client.post("/api/payments/checkout", json=_payload())
    assert r.status_code == 400 and r.get_json()["error"] == "online_only"


def test_checkout_price_is_server_side_and_generic(client, app, fake_stripe):
    r = client.post("/api/payments/checkout", json=_online(price=1))
    assert r.status_code == 201
    kw = fake_stripe["sessions"][0]
    assert kw["line_items"][0]["price_data"]["unit_amount"] == 5000
    # No consultation type (health data) is sent to Stripe.
    assert "gravidez" not in str(kw).lower()
    assert kw["payment_method_options"] == {"card": {"capture_method": "manual"},
                                            "paypal": {"capture_method": "manual"}}
    # The dashboard decides the methods; an inactive one must not break checkout.
    assert "payment_method_types" not in kw
    assert kw["excluded_payment_method_types"] == ["multibanco"]
    with app.app_context():
        b = Booking.query.one()
        assert b.status == "aguarda_pagamento" and b.payment_status == "pending"


def test_checkout_holds_slot_until_hold_expires(client, app, fake_stripe):
    _checkout(client)
    day = _future_monday()
    with app.app_context():
        assert len(app_module.db_busy_intervals(day)) == 1
        b = Booking.query.one()
        b.hold_expires_at = utcnow() - timedelta(minutes=1)
        db.session.commit()
        assert app_module.db_busy_intervals(day) == []


def test_pending_past_deadline_frees_slot(client, app, fake_stripe):
    with app.app_context():
        b = _authorized(capture_before=utcnow() - timedelta(minutes=1))
        assert app_module.db_busy_intervals(b.slot_date) == []


def test_abandoned_checkout_frees_slot_at_once(client, app, monkeypatch, fake_stripe):
    expired = []
    monkeypatch.setattr(payments.stripe.checkout.Session, "expire", lambda sid: expired.append(sid))
    ref = _checkout(client)
    assert client.post(f"/api/payments/{ref}/abandon").status_code == 200
    assert expired == ["cs_1"]
    with app.app_context():
        b = Booking.query.one()
        assert (b.status, b.payment_status) == ("cancelado", "expired")
        assert app_module.db_busy_intervals(b.slot_date) == []


def test_abandon_ignores_paid_bookings(client, app, fake_stripe):
    with app.app_context():
        _authorized()
    client.post("/api/payments/IB-TEST0001/abandon")
    with app.app_context():
        assert Booking.query.one().status == "pendente"


# ---- webhook ----

def test_webhook_bad_signature(client, fake_stripe):
    r = client.post("/api/stripe/webhook", data=b"{}", headers={"Stripe-Signature": "nope"})
    assert r.status_code == 400


def test_completed_card_is_authorized_and_emails_once(client, app, monkeypatch, fake_stripe):
    ref = _checkout(client)
    assert _complete(client, monkeypatch, ref).status_code == 200
    assert _complete(client, monkeypatch, ref).status_code == 200  # replay
    with app.app_context():
        b = Booking.query.one()
        assert (b.status, b.payment_status, b.payment_method_type) == ("pendente", "authorized", "card")
        assert b.capture_before is not None and b.amount_paid is None
    assert [e[0] for e in fake_stripe["emails"]] == [
        "send_booking_received_client", "send_nutritionist_new_booking"]


def test_payment_completing_after_cancel_is_released(client, app, monkeypatch, fake_stripe):
    ref = _checkout(client)
    with app.app_context():
        b = Booking.query.one()
        b.status = "cancelado"
        db.session.commit()
    _complete(client, monkeypatch, ref)
    assert fake_stripe["cancels"] == ["pi_1"]
    assert fake_stripe["emails"] == []
    with app.app_context():
        b = Booking.query.one()
        assert (b.status, b.payment_status) == ("cancelado", "released")


def test_completed_mb_way_is_paid(client, app, monkeypatch, fake_stripe):
    fake_stripe["pi"].update(status="succeeded", amount_received=5000, type="mb_way")
    ref = _checkout(client)
    _complete(client, monkeypatch, ref)
    with app.app_context():
        b = Booking.query.one()
        assert (b.payment_status, float(b.amount_paid)) == ("paid", 50.0)


def test_expired_checkout_cancels(client, app, monkeypatch, fake_stripe):
    _checkout(client)
    with app.app_context():
        sid = Booking.query.one().stripe_session_id
    _event(monkeypatch, "checkout.session.expired", NS(id=sid))
    client.post("/api/stripe/webhook", data=b"{}")
    with app.app_context():
        b = Booking.query.one()
        assert (b.status, b.payment_status) == ("cancelado", "expired")


def test_lapsed_hold_webhook_cancels_and_emails(client, app, monkeypatch, fake_stripe):
    with app.app_context():
        _authorized()
    _event(monkeypatch, "payment_intent.canceled", NS(id="pi_1"))
    client.post("/api/stripe/webhook", data=b"{}")
    with app.app_context():
        b = Booking.query.one()
        assert (b.status, b.payment_status) == ("cancelado", "released")
    assert ("send_payment_expired_client", "IB-TEST0001") in fake_stripe["emails"]


def test_dashboard_refund_is_synced(client, app, monkeypatch, fake_stripe):
    with app.app_context():
        _paid_booking()
    _event(monkeypatch, "charge.refunded", NS(payment_intent="pi_1", amount_refunded=5000))
    client.post("/api/stripe/webhook", data=b"{}")
    with app.app_context():
        b = Booking.query.one()
        assert (b.payment_status, float(b.amount_refunded)) == ("refunded", 50.0)


# ---- confirmation captures ----

def test_email_confirm_captures(client, app, fake_stripe):
    import auth
    with app.app_context():
        _authorized()
        token = auth.sign_booking_action("IB-TEST0001", "confirm")
    client.post("/api/bookings/action", data={"token": token})
    assert fake_stripe["captures"] == ["pi_1"]
    with app.app_context():
        b = Booking.query.one()
        assert (b.status, b.payment_status, float(b.amount_paid)) == ("confirmado", "paid", 50.0)


def test_failed_capture_does_not_confirm(client, app, monkeypatch, fake_stripe):
    import auth

    def boom(pi_id):
        raise stripe.InvalidRequestError("authorization expired", None)
    monkeypatch.setattr(payments.stripe.PaymentIntent, "capture", boom)
    with app.app_context():
        _authorized()
        token = auth.sign_booking_action("IB-TEST0001", "confirm")
    r = client.post("/api/bookings/action", data={"token": token})
    assert r.status_code == 409
    _auth(client)
    r = client.put("/api/admin/bookings/IB-TEST0001", json={"status": "confirmado"})
    assert r.status_code == 409 and r.get_json()["error"] == "capture_failed"
    with app.app_context():
        assert Booking.query.one().status == "pendente"


def test_admin_reschedule_and_confirm_captures(client, app, fake_stripe):
    with app.app_context():
        _authorized(status="revisao")
    _auth(client)
    new_day = (date.today() + timedelta(days=12)).isoformat()
    r = client.put("/api/admin/bookings/IB-TEST0001",
                   json={"slot_date": new_day, "status": "confirmado", "notify": False})
    assert r.status_code == 200, r.get_json()
    assert fake_stripe["captures"] == ["pi_1"]
    # Saving a confirmed booking again must not capture twice.
    client.put("/api/admin/bookings/IB-TEST0001", json={"nome": "Outro", "notify": False})
    assert fake_stripe["captures"] == ["pi_1"]


# ---- cancellations and refunds ----

def _client_cancel(client):
    return client.put("/api/bookings/IB-TEST0001/cancel", json={"email": "cliente@teste.pt"})


def test_client_cancel_with_notice_refunds_in_full(client, app, fake_stripe):
    with app.app_context():
        _paid_booking()
    r = _client_cancel(client)
    assert r.status_code == 200 and r.get_json()["refunded"] == 50.0
    assert fake_stripe["refunds"][0]["amount"] == 5000


def test_client_cancel_inside_notice_no_refund(client, app, fake_stripe):
    with app.app_context():
        _paid_booking(**_soon())
    r = _client_cancel(client)
    assert r.status_code == 200 and r.get_json()["refunded"] == 0
    assert fake_stripe["refunds"] == []


def test_client_cancel_releases_hold_even_inside_notice(client, app, fake_stripe):
    with app.app_context():
        _authorized(**_soon())
    _client_cancel(client)
    assert fake_stripe["cancels"] == ["pi_1"]
    with app.app_context():
        assert Booking.query.one().payment_status == "released"


def test_admin_partial_refunds_accumulate_and_cap(client, app, fake_stripe):
    with app.app_context():
        _paid_booking()
    _auth(client)
    url = "/api/admin/bookings/IB-TEST0001/refund"
    assert client.post(url, json={"amount": 20}).status_code == 200
    assert client.post(url, json={"amount": 31}).status_code == 409  # only 30 left
    r = client.post(url, json={})
    assert r.status_code == 200 and r.get_json()["refunded"] == 30.0
    assert client.post(url, json={}).status_code == 400  # nothing left
    with app.app_context():
        b = Booking.query.one()
        assert (b.payment_status, float(b.amount_refunded)) == ("refunded", 50.0)
    assert [r["amount"] for r in fake_stripe["refunds"]] == [2000, 3000]


def test_admin_cancel_refund_optional(client, app, fake_stripe):
    with app.app_context():
        _paid_booking()
    _auth(client)
    client.post("/api/admin/bookings/IB-TEST0001/cancel", json={"refund": False})
    assert fake_stripe["refunds"] == []
    with app.app_context():
        assert Booking.query.one().status == "cancelado"


def test_overdue_sweep_refunds_mb_way(client, app, fake_stripe):
    with app.app_context():
        _paid_booking(status="pendente", capture_before=utcnow() - timedelta(minutes=1))
    _auth(client)
    client.get("/api/admin/bookings")
    assert fake_stripe["refunds"][0]["amount"] == 5000
    with app.app_context():
        assert Booking.query.one().status == "cancelado"
    assert ("send_payment_expired_client", "IB-TEST0001") in fake_stripe["emails"]


def test_purge_keeps_paid_bookings(client, app, fake_stripe):
    old = date.today() - timedelta(days=400)
    with app.app_context():
        _paid_booking(status="cancelado", slot_date=old)
        make_booking(reference="IB-OLD", status="cancelado", slot_date=old)
    _auth(client)
    client.get("/api/admin/bookings")
    with app.app_context():
        assert [b.reference for b in Booking.query.all()] == ["IB-TEST0001"]
