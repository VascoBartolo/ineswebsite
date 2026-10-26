"""Stripe webhook: the only writer of payment outcomes. The browser's return from
Checkout proves nothing (the tab can close, the URL can be forged)."""
import logging

import stripe
from flask import Blueprint, request, jsonify

import calendar_service
import email_service
import payments
from models import db, Booking, utcnow

logger = logging.getLogger("ibnutricao.payments")

payment_bp = Blueprint("payments", __name__, url_prefix="/api/stripe")


@payment_bp.route("/webhook", methods=["POST"])
def webhook():
    try:
        event = stripe.Webhook.construct_event(
            request.get_data(), request.headers.get("Stripe-Signature", ""), payments.WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError):
        logger.warning("Stripe webhook with invalid payload or signature")
        return jsonify({"error": "invalid_signature"}), 400

    obj = event.data.object
    kind = event.type
    if kind in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        _session_completed(obj)
    elif kind in ("checkout.session.expired", "checkout.session.async_payment_failed"):
        _session_failed(obj)
    elif kind == "payment_intent.canceled":
        _hold_canceled(obj)
    elif kind == "charge.refunded":
        booking = Booking.query.filter_by(stripe_payment_intent=obj.payment_intent).first()
        if booking:
            payments.sync_refunds(booking, obj)
            db.session.commit()
    # Anything else is acknowledged, so Stripe does not retry it.
    return jsonify({"received": True})


def _session_completed(session):
    booking = Booking.query.filter_by(stripe_session_id=session.id).first()
    if not booking:
        logger.error("Completed Checkout %s matches no booking", session.id)
        return
    cancelled = booking.status == "cancelado"
    if not payments.apply_completed_session(booking, session):
        return  # replayed event, or payment still processing
    if cancelled:
        # Cancelled while the client was still paying: give the money back.
        booking.status = "cancelado"
        try:
            payments.release_or_refund(booking)
        except payments.PaymentError as e:
            logger.error("Refund of payment for cancelled %s failed: %s", booking.reference, e)
        db.session.commit()
        return
    db.session.commit()
    logger.info("Payment %s for %s", booking.payment_status, booking.reference)
    email_service.send_booking_received_client(booking)
    email_service.send_nutritionist_new_booking(booking)


def _session_failed(session):
    booking = Booking.query.filter_by(stripe_session_id=session.id).first()
    if booking and booking.status == "aguarda_pagamento":
        booking.status = "cancelado"
        booking.payment_status = "expired"
        booking.hold_expires_at = None
        db.session.commit()


def _hold_canceled(pi):
    # Our own releases already set payment_status to released, so only a hold
    # Stripe let lapse gets here.
    booking = Booking.query.filter_by(stripe_payment_intent=pi.id).first()
    if booking and booking.payment_status == "authorized":
        booking.payment_status = "released"
        if booking.status == "cancelado":
            db.session.commit()  # already cancelled (e.g. from the edit modal): nothing to tell
        else:
            _cancel_expired(booking, refunded=0)


def _cancel_expired(booking, refunded):
    booking.status = "cancelado"
    booking.updated_at = utcnow()
    if booking.google_event_id:
        calendar_service.delete_event(booking.google_event_id)
        booking.google_event_id = None
    db.session.commit()
    logger.info("Booking %s lapsed unconfirmed (refunded %s)", booking.reference, refunded)
    email_service.send_payment_expired_client(booking, refunded)


def expire_overdue():
    """Cancel requests the nutritionist did not confirm before the payment
    deadline: release the hold, or refund MB WAY, which was charged at once.
    shortcut: runs when the admin panel lists bookings (and card/PayPal holds also
    via the payment_intent.canceled webhook); move to an ACA Job if MB WAY
    bookings can sit unrefunded for days while the panel goes unopened."""
    overdue = Booking.query.filter(
        Booking.status.in_(["pendente", "revisao"]),
        Booking.payment_status.in_(["authorized", "paid"]),
        Booking.capture_before < utcnow(),
    ).all()
    for booking in overdue:
        try:
            refunded = payments.release_or_refund(booking)
        except payments.PaymentError as e:
            # A lapsed hold can no longer be cancelled; nothing was charged.
            if booking.payment_status != "authorized":
                logger.error("Overdue refund failed for %s: %s", booking.reference, e)
                continue
            booking.payment_status = "released"
            refunded = 0
        _cancel_expired(booking, refunded)
