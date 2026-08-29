"""Token-authorized booking actions triggered from the nutritionist's notification
email (Confirmar / Solicitar Alteração).

The nutritionist is not logged in when she clicks a link in her inbox, so each link
carries a signed, time-limited token (see auth.sign_booking_action) that binds one
booking reference to one action. That signature is the authorization.

The email link is a GET that only *renders* a confirmation page; the state change
happens on the POST from that page. This two-step keeps email-client / anti-malware
link prefetchers — which issue GETs — from firing the action by accident.
"""
import logging

from flask import Blueprint, request, Response
from markupsafe import escape

import auth
from models import db, Booking
import calendar_service
import email_service

logger = logging.getLogger("ibnutricao.booking_action")

booking_action_bp = Blueprint("booking_action", __name__, url_prefix="/api/bookings")

_ACTION_LABEL = {"confirm": "Confirmar Consulta", "revise": "Solicitar Alteração"}


def _page(heading, message, *, accent="#B94448", status=200):
    """A small self-contained branded HTML page (no external assets)."""
    html = f"""<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>IB Nutrição</title>
</head>
<body style="margin:0;background:#FDF7F7;font-family:'Jost',Arial,sans-serif;color:#2C1A1A;">
  <div style="max-width:520px;margin:48px auto;background:white;border-radius:12px;
              padding:40px 32px;box-shadow:0 4px 24px rgba(0,0,0,0.06);text-align:center;">
    <h1 style="font-family:Georgia,serif;font-weight:400;color:{accent};font-size:1.5rem;margin-top:0;">{heading}</h1>
    <div style="color:#2C1A1A;font-size:1rem;line-height:1.6;">{message}</div>
  </div>
</body>
</html>"""
    return Response(html, status=status, mimetype="text/html")


def _confirm_form(token, action, booking):
    label = _ACTION_LABEL[action]
    accent = "#5A8A5A" if action == "confirm" else "#B94448"
    if action == "confirm":
        intro = ("Vai <strong>confirmar</strong> esta consulta. O cliente receberá um "
                 "email a informar que a consulta foi confirmada.")
    else:
        intro = ("Vai <strong>solicitar uma alteração</strong>. O cliente será informado "
                 "de que a disponibilidade mudou e de que entrará em contacto para remarcar.")
    summary = (f"<div style='background:#FDF7F7;border-radius:8px;padding:16px;margin:20px 0;"
               f"text-align:left;font-size:0.92rem;'>"
               f"<div><strong>Referência:</strong> {escape(booking.reference)}</div>"
               f"<div><strong>Cliente:</strong> {escape(booking.nome)}</div>"
               f"<div><strong>Data:</strong> {email_service._fmt_date(booking.slot_date)}</div>"
               f"<div><strong>Hora:</strong> {booking.slot_time.strftime('%H:%M')}</div>"
               f"</div>")
    body = f"""
    <p>{intro}</p>
    {summary}
    <form method="post" action="/api/bookings/action" style="margin-top:24px;">
      <input type="hidden" name="token" value="{escape(token)}">
      <button type="submit"
              style="background:{accent};color:white;border:none;font-weight:600;
                     padding:14px 32px;border-radius:8px;font-size:1rem;cursor:pointer;">{label}</button>
    </form>
    """
    return _page(label, body, accent=accent)


def _load(token):
    """Resolve a token to (data, booking). Either may be None."""
    data = auth.verify_booking_action(token)
    if not data:
        return None, None
    booking = Booking.query.filter_by(reference=data["ref"]).first()
    return data, booking


@booking_action_bp.route("/action", methods=["GET"])
def action_page():
    token = request.args.get("token", "")
    data, booking = _load(token)
    if not data or not booking:
        logger.warning("Booking action GET with invalid/unknown token")
        return _page("Ligação inválida",
                     "Esta ligação é inválida ou expirou. Por favor consulte o email original.",
                     status=400)
    if booking.status == "cancelado":
        return _page("Consulta cancelada",
                     f"A consulta <strong>{escape(booking.reference)}</strong> foi cancelada, "
                     "pelo que não é possível efetuar esta ação.")
    return _confirm_form(token, data["action"], booking)


@booking_action_bp.route("/action", methods=["POST"])
def action_execute():
    token = request.form.get("token", "")
    data, booking = _load(token)
    if not data or not booking:
        logger.warning("Booking action POST with invalid/unknown token")
        return _page("Ligação inválida",
                     "Esta ligação é inválida ou expirou. Por favor consulte o email original.",
                     status=400)

    action, ref = data["action"], booking.reference

    if booking.status == "cancelado":
        return _page("Consulta cancelada",
                     f"A consulta <strong>{escape(ref)}</strong> foi cancelada, "
                     "pelo que não é possível efetuar esta ação.")

    target = "confirmado" if action == "confirm" else "revisao"

    # Idempotent: repeated clicks (or a prefetch that slipped through) must not
    # re-run the side effects (calendar event, client email).
    if booking.status == target:
        logger.info("Booking action %s no-op (already %s) for %s", action, target, ref)
        return _already_done_page(action, ref)

    booking.status = target
    if action == "confirm":
        # Approval is the moment the appointment enters her calendar.
        try:
            booking.google_event_id = calendar_service.create_event(booking)
        except Exception as e:
            logger.error("Booking confirm: calendar event failed for %s: %s", ref, e)
    elif booking.google_event_id:
        # Rejected after a prior confirm: remove it from the calendar so it stops
        # holding the slot and doesn't linger in the agenda.
        try:
            calendar_service.delete_event(booking.google_event_id)
        except Exception as e:
            logger.error("Booking revise: calendar delete failed for %s: %s", ref, e)
        booking.google_event_id = None
    db.session.commit()

    try:
        if action == "confirm":
            email_service.send_booking_confirmed_client(booking)
        else:
            email_service.send_booking_review_client(booking)
    except Exception as e:
        logger.error("Booking action %s: client email failed for %s: %s", action, ref, e)

    logger.info("Booking action %s applied to %s (status=%s)", action, ref, target)

    if action == "confirm":
        return _page("Consulta confirmada ✓",
                     f"A consulta <strong>{escape(ref)}</strong> foi confirmada. "
                     "O cliente foi notificado por email.",
                     accent="#5A8A5A")
    return _page("Alteração solicitada",
                 f"O cliente da consulta <strong>{escape(ref)}</strong> foi informado de que "
                 "a disponibilidade mudou e de que irá entrar em contacto para remarcar.")


def _already_done_page(action, ref):
    if action == "confirm":
        return _page("Já confirmada",
                     f"A consulta <strong>{escape(ref)}</strong> já tinha sido confirmada. "
                     "Não foi enviado novo email.",
                     accent="#5A8A5A")
    return _page("Alteração já solicitada",
                 f"A consulta <strong>{escape(ref)}</strong> já tinha sido marcada para revisão. "
                 "Não foi enviado novo email.")
