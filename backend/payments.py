"""Stripe payments for online consultations. The only module that calls Stripe.

Cards (incl. Apple Pay / Google Pay) and PayPal are authorized at booking and
captured when the nutritionist confirms. MB WAY cannot be held, so it is charged
at once and refunded if the booking is never confirmed.
"""
import os
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import stripe

import calendar_service
import legal
from models import utcnow

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
SITE_URL = os.environ.get("SITE_URL", "https://inesbandarranutricao.com")

# Stripe's minimum Checkout lifetime is 30 min; our slot hold outlasts it so a
# client still on the payment page never loses the slot to someone else.
CHECKOUT_LIFETIME = timedelta(minutes=31)
SLOT_HOLD = timedelta(minutes=35)
# Confirmation deadline when Stripe gives none (PayPal, MB WAY). Below the
# shortest card hold, so one rule fits every method.
CONFIRM_WINDOW = timedelta(days=5)
# A payment link the nutritionist sends for a booking she created. 24h is
# Stripe's maximum Checkout lifetime; the hold again outlasts it.
LINK_LIFETIME = timedelta(hours=23, minutes=55)
LINK_HOLD = timedelta(hours=24)

# Which methods appear is set in the Stripe dashboard, so one that is not yet
# activated (e.g. PayPal pending approval) can't break checkout. Multibanco is
# settled days later, long after the slot hold, so it is never offered.
EXCLUDED_METHODS = ["multibanco"]


class PaymentError(Exception):
    pass


def enabled():
    return bool(stripe.api_key)


def _cents(amount):
    return int((Decimal(str(amount)) * 100).to_integral_value())


def _euros(cents):
    return Decimal(cents) / 100


def create_checkout(booking, admin_link=False):
    """Open a Checkout Session for a booking already in aguarda_pagamento.

    admin_link: a booking the nutritionist created herself, so it is charged at
    once and confirmed on payment, with no approval step."""
    if admin_link:
        lifetime, hold = LINK_LIFETIME, LINK_HOLD
        extra = {
            "metadata": {"admin_link": "1"},
            "consent_collection": {"terms_of_service": "required"},
            "custom_text": {"submit": {"message": (
                f"O pagamento confirma a consulta {booking.reference} de "
                f"{booking.slot_date.strftime('%d/%m/%Y')} às {booking.slot_time.strftime('%H:%M')} "
                "(hora dos Açores). Este link é válido durante 24 horas; se não for pago até lá, "
                "o horário é libertado.")}},
        }
        # No cancel_url, so no back button: returning would abandon (cancel) the booking.
        result = "confirmado"
    else:
        lifetime, hold = CHECKOUT_LIFETIME, SLOT_HOLD
        extra = {"payment_method_options": {
            "card": {"capture_method": "manual"},
            "paypal": {"capture_method": "manual"},
        }, "cancel_url": f"{SITE_URL}/marcar-consulta?pagamento=cancelado&ref={booking.reference}"}
        result = "ok"
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "quantity": 1,
            "price_data": {
                "currency": "eur",
                "unit_amount": _cents(booking.price),
                # Generic on purpose: tipo_consulta can reveal health data
                # ("Consulta na Gravidez") and must not reach Stripe.
                "product_data": {"name": "Consulta de nutrição online"},
            },
        }],
        excluded_payment_method_types=EXCLUDED_METHODS,
        payment_intent_data={"description": booking.reference},
        customer_email=booking.email,
        client_reference_id=booking.reference,
        locale="pt",
        expires_at=int(time.time() + lifetime.total_seconds()),
        success_url=f"{SITE_URL}/marcar-consulta?pagamento={result}&ref={booking.reference}",
        **extra,
    )
    booking.stripe_session_id = session.id
    booking.payment_status = "pending"
    booking.hold_expires_at = utcnow() + hold
    return session


def checkout_url(booking):
    """The open Checkout's URL, to copy the payment link again."""
    return stripe.checkout.Session.retrieve(booking.stripe_session_id).url


def is_admin_link(session):
    # A StripeObject is not a dict: read keys as attributes.
    return getattr(getattr(session, "metadata", None), "admin_link", None) == "1"


def expire_checkout(booking):
    """Close an unpaid Checkout. False when Stripe refuses (it was paid after all,
    and the webhook will record it)."""
    try:
        stripe.checkout.Session.expire(booking.stripe_session_id)
    except stripe.StripeError:
        return False
    booking.payment_status = "expired"
    booking.hold_expires_at = None
    return True


def apply_completed_session(booking, session):
    """Record the outcome of a completed Checkout. Returns True when the booking
    moved out of aguarda_pagamento (so the caller sends the emails once)."""
    if booking.payment_status not in ("pending", "expired"):
        return False
    pi = stripe.PaymentIntent.retrieve(session.payment_intent, expand=["latest_charge"])
    details = getattr(pi.latest_charge, "payment_method_details", None)
    now = utcnow()
    booking.stripe_payment_intent = pi.id
    booking.payment_method_type = getattr(details, "type", None)
    if pi.status == "requires_capture":
        booking.payment_status = "authorized"
        card_deadline = getattr(getattr(details, "card", None), "capture_before", None)
        booking.capture_before = (
            datetime.fromtimestamp(card_deadline, timezone.utc).replace(tzinfo=None)
            if card_deadline else now + CONFIRM_WINDOW)
    elif pi.status == "succeeded":
        booking.payment_status = "paid"
        booking.amount_paid = _euros(pi.amount_received)
        booking.paid_at = now
        booking.capture_before = now + CONFIRM_WINDOW
    else:
        # Still processing: the async_payment_* webhook finishes the job.
        return False
    booking.status = "pendente"
    if is_admin_link(session):
        booking.status = "confirmado"
        booking.capture_before = None
        consent = getattr(session, "consent", None)
        if getattr(consent, "terms_of_service", None) == "accepted":
            booking.terms_accepted_at = now
            booking.terms_version = legal.TERMS_VERSION
    booking.hold_expires_at = None
    booking.updated_at = now
    return True


def capture(booking):
    """Charge a held payment. No-op for bookings with nothing held. Raises
    PaymentError when the hold can no longer be captured."""
    if booking.payment_status != "authorized":
        return
    try:
        pi = stripe.PaymentIntent.capture(booking.stripe_payment_intent)
    except stripe.StripeError as e:
        raise PaymentError(str(e)) from e
    booking.payment_status = "paid"
    booking.amount_paid = _euros(pi.amount_received)
    booking.paid_at = utcnow()


def refundable(booking):
    """What is left to refund, in euros."""
    if booking.payment_status != "paid":
        return Decimal(0)
    return Decimal(booking.amount_paid or 0) - Decimal(booking.amount_refunded or 0)


def release_or_refund(booking, amount=None):
    """Cancel a hold, or refund `amount` euros (default: everything left).
    Returns the euros refunded (0 for a released hold or nothing to do)."""
    try:
        if booking.payment_status == "authorized":
            stripe.PaymentIntent.cancel(booking.stripe_payment_intent)
            booking.payment_status = "released"
            return Decimal(0)
        remaining = refundable(booking)
        if amount is None and remaining <= 0:
            return Decimal(0)
        amt = remaining if amount is None else Decimal(str(amount))
        if not 0 < amt <= remaining:
            raise PaymentError("invalid_refund_amount")
        already = Decimal(booking.amount_refunded or 0)
        stripe.Refund.create(
            payment_intent=booking.stripe_payment_intent,
            amount=_cents(amt),
            # A double-submitted refund of the same amount from the same state is one refund.
            idempotency_key=f"refund-{booking.reference}-{_cents(already)}-{_cents(amt)}",
        )
    except stripe.StripeError as e:
        raise PaymentError(str(e)) from e
    _set_refunded(booking, already + amt)
    return amt


def _set_refunded(booking, total):
    booking.amount_refunded = total
    if total >= Decimal(booking.amount_paid or 0):
        booking.payment_status = "refunded"


def sync_refunds(booking, charge):
    """Mirror refunds made anywhere (incl. the Stripe dashboard) from a charge."""
    total = _euros(charge.amount_refunded)
    if booking.payment_status == "paid" and total > Decimal(booking.amount_refunded or 0):
        _set_refunded(booking, total)


def within_notice(booking):
    """True when the slot is far enough ahead for a refunded client cancellation."""
    slot = datetime.combine(booking.slot_date, booking.slot_time)
    return slot - calendar_service.now_azores() >= timedelta(hours=legal.CANCELLATION_NOTICE_HOURS)


def client_cancel(booking):
    """Apply the Terms §8 refund rule to a client cancellation. A hold is always
    released (she never accepted the booking); a charge is refunded only with
    enough notice. Returns the euros refunded."""
    if booking.payment_status == "authorized" or within_notice(booking):
        return release_or_refund(booking)
    return Decimal(0)


def deadline_passed(booking):
    return bool(booking.capture_before) and booking.capture_before < utcnow()
