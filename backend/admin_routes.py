import time
from datetime import date as _date
from flask import Blueprint, request, jsonify

import auth
from models import db, Booking, generate_unique_reference
import stats as stats_mod
import calendar_service
import email_service

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True) or {}
    password = data.get("password") or ""
    if not auth.verify_password(password):
        time.sleep(auth.LOGIN_FAIL_DELAY)
        return jsonify({"error": "invalid_credentials"}), 401
    resp = jsonify({"ok": True})
    return auth.set_auth_cookie(resp, auth.issue_token())


@admin_bp.route("/logout", methods=["POST"])
def logout():
    resp = jsonify({"ok": True})
    return auth.clear_auth_cookie(resp)


@admin_bp.route("/session")
def session():
    token = request.cookies.get(auth.COOKIE_NAME)
    return jsonify({"authenticated": auth.verify_token(token)})


def _booking_admin_dict(b):
    d = b.to_dict()
    d["idade"] = b.idade
    d["duration_minutes"] = b.duration_minutes
    d["updated_at"] = b.updated_at.isoformat() if b.updated_at else None
    d["is_first"] = b.is_first
    return d


def _sync_calendar(booking):
    """Reconcile the Google Calendar event with the booking's status: a confirmed
    booking must have an up-to-date event; any other status must have none. This
    pushes admin date/time/detail edits straight to the agenda, creates the event
    when an admin re-confirms a cancelled/pending booking, and removes it when a
    booking is moved out of the confirmed state."""
    if booking.status == "confirmado":
        booking.google_event_id = calendar_service.update_event(booking.google_event_id, booking)
    elif booking.google_event_id:
        calendar_service.delete_event(booking.google_event_id)
        booking.google_event_id = None


@admin_bp.route("/bookings")
@auth.require_admin
def list_bookings():
    q = Booking.query
    status = request.args.get("status", "all")
    regime = request.args.get("regime", "all")
    local = request.args.get("local_consulta", "").strip()
    sujeito = request.args.get("sujeito", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    search = request.args.get("q", "").strip().lower()

    if status in ("pendente", "confirmado", "revisao", "cancelado"):
        q = q.filter(Booking.status == status)
    if regime in ("presencial", "online"):
        q = q.filter(db.func.lower(Booking.regime) == regime)
    if local:
        q = q.filter(Booking.local_consulta == local)
    if sujeito:
        q = q.filter(Booking.sujeito == sujeito)
    if date_from:
        q = q.filter(Booking.slot_date >= _date.fromisoformat(date_from))
    if date_to:
        q = q.filter(Booking.slot_date <= _date.fromisoformat(date_to))
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{escaped}%"
        q = q.filter(db.or_(
            db.func.lower(Booking.nome).like(like),
            db.func.lower(Booking.email).like(like),
            db.func.lower(Booking.reference).like(like),
        ))

    # Date is the only sortable column the table offers; anything else falls back
    # to it. `id` breaks ties so paging is stable: two bookings sharing a date and
    # time would otherwise come back in an arbitrary order per query, which can
    # repeat or skip a row between pages.
    if request.args.get("order", "desc").lower() == "asc":
        q = q.order_by(Booking.slot_date.asc(), Booking.slot_time.asc(), Booking.id.asc())
    else:
        q = q.order_by(Booking.slot_date.desc(), Booking.slot_time.desc(), Booking.id.desc())

    page = max(1, int(request.args.get("page", 1)))
    per_page = min(100, max(1, int(request.args.get("per_page", 30))))
    total = q.count()
    rows = q.offset((page - 1) * per_page).limit(per_page).all()

    # Drop the ORDER BY (slot_date/slot_time) before aggregating: an aggregate-only
    # SELECT with no GROUP BY cannot carry an ORDER BY on non-grouped columns —
    # PostgreSQL rejects it (SQLite silently allows it, which is why tests miss it).
    agg = q.order_by(None).with_entities(
        db.func.count().label("cnt"),
        db.func.count(db.case((Booking.status == "confirmado", 1))).label("confirmed"),
        db.func.coalesce(
            db.func.sum(db.case((Booking.status == "confirmado", Booking.price), else_=0)),
            0,
        ).label("faturado"),
    ).first()

    bookings = [_booking_admin_dict(b) for b in rows]
    pages = max(1, (total + per_page - 1) // per_page)
    return jsonify({
        "bookings": bookings,
        "summary": {
            "count": agg.cnt,
            "confirmed_count": agg.confirmed,
            "faturado": round(float(agg.faturado), 2),
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages,
        },
    })


@admin_bp.route("/stats")
@auth.require_admin
def stats_view():
    regime = request.args.get("regime", "all")
    local = request.args.get("local_consulta", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    group_by = request.args.get("group_by", "week")
    if group_by not in ("day", "week", "month"):
        group_by = "week"

    q = Booking.query
    if regime in ("presencial", "online"):
        q = q.filter(db.func.lower(Booking.regime) == regime)
    if local:
        q = q.filter(Booking.local_consulta == local)
    if date_from:
        q = q.filter(Booking.slot_date >= _date.fromisoformat(date_from))
    if date_to:
        q = q.filter(Booking.slot_date <= _date.fromisoformat(date_to))

    rows = [{
        "regime": b.regime, "price": b.price, "status": b.status,
        "local_consulta": b.local_consulta, "slot_date": b.slot_date,
    } for b in q.all()]

    result = stats_mod.summarize(rows)
    result["series"] = stats_mod.build_series(rows, group_by)
    result["group_by"] = group_by
    return jsonify(result)


@admin_bp.route("/locations")
@auth.require_admin
def locations_view():
    rows = (db.session.query(Booking.local_consulta)
            .filter(Booking.local_consulta.isnot(None))
            .distinct().all())
    locs = sorted({r[0] for r in rows if r[0]})
    return jsonify({"locations": locs})


EDITABLE_FIELDS = {
    "nome", "email", "contacto", "idade", "sujeito", "tipo_consulta",
    "regime", "local_consulta", "duration_minutes", "price", "contexto", "status",
}


# Everything the admin must supply to create a booking by hand. `contexto` and
# `local_consulta` are optional, and `status` defaults below.
CREATE_REQUIRED = (
    "nome", "email", "contacto", "idade", "sujeito", "tipo_consulta",
    "regime", "slot_date", "slot_time", "duration_minutes", "price",
)

VALID_STATUSES = ("pendente", "confirmado", "revisao", "cancelado")


def _parse_is_first(value):
    """Three-state: True (primeira), False (seguimento), None (not recorded).

    An empty string is the admin leaving the field blank, which must stay NULL
    rather than collapsing to False — "not recorded" and "seguimento" are
    different facts.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "primeira")


@admin_bp.route("/bookings", methods=["POST"])
@auth.require_admin
def create_booking_admin():
    """Manual entry from the admin table.

    Deliberately skips the availability check the public form runs: she is
    recording a consultation already agreed with the client, so she must be able
    to place it on an occupied slot, outside the working windows, or on a
    feriado. Judging a collision is hers, not the booking rules'.
    """
    from datetime import date as d, time as t
    data = request.get_json(force=True) or {}

    # Emptiness, not falsiness — a price of 0 is a legitimate value.
    missing = [f for f in CREATE_REQUIRED if data.get(f) in (None, "")]
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    try:
        slot_date = d.fromisoformat(str(data["slot_date"]))
        hh, mm = str(data["slot_time"]).split(":")[:2]
        slot_time = t(int(hh), int(mm))
        duration = int(data["duration_minutes"])
        price = float(data["price"])
    except (ValueError, AttributeError, TypeError):
        return jsonify({"error": "invalid_fields"}), 400

    status = data.get("status") or "confirmado"
    if status not in VALID_STATUSES:
        return jsonify({"error": "invalid_status"}), 400

    regime = str(data["regime"]).strip()
    local = (data.get("local_consulta") or "").strip() or None
    if regime.lower() == "online":
        local = None

    booking = Booking(
        reference=generate_unique_reference(),
        sujeito=str(data["sujeito"]).strip(),
        tipo_consulta=str(data["tipo_consulta"]).strip(),
        regime=regime,
        local_consulta=local,
        nome=str(data["nome"]).strip(),
        idade=str(data["idade"]).strip()[:50],
        email=str(data["email"]).strip().lower(),
        contacto=str(data["contacto"]).strip(),
        contexto=(data.get("contexto") or "").strip() or None,
        slot_date=slot_date,
        slot_time=slot_time,
        duration_minutes=duration,
        price=price,
        is_first=_parse_is_first(data.get("is_first")),
        status=status,
    )
    db.session.add(booking)
    db.session.commit()

    partial = []
    try:
        _sync_calendar(booking)
        db.session.commit()
    except Exception as e:
        partial.append(f"calendar: {e}")
    # Silence is the default: a manually entered booking is usually one already
    # agreed with the client, so notifying is the deliberate choice, not the
    # accident. (Edit defaults the other way, where a silent change is the
    # surprise.) The modal always sends the flag explicitly; this governs any
    # caller that omits it.
    #
    # A booking created straight into `revisao` or `cancelado` gets no email
    # either way: there is no prior request for either message to reply to.
    if bool(data.get("notify", False)):
        try:
            if booking.status == "confirmado":
                email_service.send_booking_confirmed_client(booking)
            elif booking.status == "pendente":
                email_service.send_booking_received_client(booking)
        except Exception as e:
            partial.append(f"email: {e}")

    return jsonify({"booking": _booking_admin_dict(booking), "partial_failures": partial}), 201


@admin_bp.route("/bookings/<reference>", methods=["PUT"])
@auth.require_admin
def edit_booking(reference):
    from datetime import date as d, time as t
    booking = Booking.query.filter_by(reference=reference.upper()).first()
    if not booking:
        return jsonify({"error": "not_found"}), 404

    data = request.get_json(force=True) or {}
    # The admin chooses per-save whether the client is emailed the new details.
    notify = bool(data.get("notify", True))
    for field in EDITABLE_FIELDS:
        if field in data and data[field] is not None:
            setattr(booking, field, data[field])
    if "slot_date" in data and data["slot_date"]:
        booking.slot_date = d.fromisoformat(data["slot_date"])
    if "slot_time" in data and data["slot_time"]:
        hh, mm = str(data["slot_time"]).split(":")
        booking.slot_time = t(int(hh), int(mm))
    if "is_first" in data:
        booking.is_first = _parse_is_first(data["is_first"])
    if booking.regime and booking.regime.lower() == "online":
        booking.local_consulta = None

    db.session.commit()

    partial = []
    try:
        _sync_calendar(booking)
        db.session.commit()
    except Exception as e:
        partial.append(f"calendar: {e}")
    if notify:
        try:
            email_service.send_booking_updated_client(booking)
        except Exception as e:
            partial.append(f"email: {e}")

    return jsonify({"booking": _booking_admin_dict(booking), "partial_failures": partial})


@admin_bp.route("/bookings/<reference>/cancel", methods=["POST"])
@auth.require_admin
def cancel_booking_admin(reference):
    from datetime import datetime
    booking = Booking.query.filter_by(reference=reference.upper()).first()
    if not booking:
        return jsonify({"error": "not_found"}), 404
    if booking.status == "cancelado":
        return jsonify({"error": "already_cancelled"}), 400
    booking.status = "cancelado"
    booking.updated_at = datetime.utcnow()
    db.session.commit()
    if booking.google_event_id:
        calendar_service.delete_event(booking.google_event_id)
    email_service.send_booking_cancelled_client(booking)
    email_service.send_nutritionist_cancellation(booking)
    return jsonify({"booking": _booking_admin_dict(booking)})


@admin_bp.route("/bookings/<reference>", methods=["DELETE"])
@auth.require_admin
def delete_booking_admin(reference):
    booking = Booking.query.filter_by(reference=reference.upper()).first()
    if not booking:
        return jsonify({"error": "not_found"}), 404
    if booking.google_event_id:
        calendar_service.delete_event(booking.google_event_id)
    db.session.delete(booking)
    db.session.commit()
    return jsonify({"ok": True})
