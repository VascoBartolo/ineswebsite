import time
from datetime import timedelta
from flask import Blueprint, request, jsonify

import auth
from models import db, Booking, LoginAttempt, generate_unique_reference, utcnow
import stats as stats_mod
import calendar_service
import email_service
import payment_routes
import payments
from validation import (
    BOOKING_LIMITS, EMAIL_RE, REGIMES, STATUSES,
    BadInput, choice, date_arg, int_arg, json_body, parse_date, parse_time, too_long,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.after_request
def renew_session(response):
    # Sliding session: active use keeps her signed in; an idle or stolen cookie
    # lapses TOKEN_MAX_AGE after its last renewal.
    if (request.endpoint not in ("admin.login", "admin.logout")
            and auth.token_needs_renewal(request.cookies.get(auth.COOKIE_NAME))):
        auth.set_auth_cookie(response, auth.issue_token())
    return response


LOGIN_MAX_FAILURES = 10
LOGIN_WINDOW = timedelta(minutes=15)


@admin_bp.route("/login", methods=["POST"])
def login():
    data = json_body()
    password = data.get("password")
    if not isinstance(password, str):
        password = ""

    ip = request.remote_addr or "unknown"
    now = utcnow()
    recent = LoginAttempt.query.filter(
        LoginAttempt.ip == ip, LoginAttempt.created_at >= now - LOGIN_WINDOW).count()
    if recent >= LOGIN_MAX_FAILURES:
        return jsonify({"error": "rate_limited",
                        "message": "Demasiadas tentativas. Tente novamente mais tarde."}), 429

    if not auth.verify_password(password):
        db.session.add(LoginAttempt(ip=ip, created_at=now))
        LoginAttempt.query.filter(LoginAttempt.created_at < now - timedelta(days=1)).delete()
        db.session.commit()
        time.sleep(auth.LOGIN_FAIL_DELAY)
        return jsonify({"error": "invalid_credentials"}), 401

    LoginAttempt.query.filter_by(ip=ip).delete()
    db.session.commit()
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
    d["payment_method_type"] = b.payment_method_type
    d["capture_before"] = b.capture_before.isoformat() if b.capture_before else None
    d["refundable"] = float(payments.refundable(b))
    d["terms_accepted_at"] = b.terms_accepted_at.isoformat() if b.terms_accepted_at else None
    d["terms_version"] = b.terms_version
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


# Privacy Policy §5: cancelled or never-confirmed bookings are kept at most 12 months.
# Purged inline like LoginAttempt, since an in-process scheduler would run once per
# gunicorn worker and replica.
# shortcut: only runs when the admin panel lists bookings; move to an ACA Job if the
# panel can go unopened for weeks.
UNCONFIRMED_RETENTION = timedelta(days=365)


def _purge_expired_bookings():
    cutoff = utcnow().date() - UNCONFIRMED_RETENTION
    Booking.query.filter(
        Booking.status != "confirmado", Booking.slot_date < cutoff,
        # Money moved: a fiscal record, kept 10 years (Privacy Policy §5).
        Booking.amount_paid.is_(None),
    ).delete(synchronize_session=False)
    db.session.commit()


@admin_bp.route("/bookings")
@auth.require_admin
def list_bookings():
    _purge_expired_bookings()
    payment_routes.expire_overdue()
    q = Booking.query
    status = request.args.get("status", "all")
    regime = request.args.get("regime", "all")
    local = request.args.get("local_consulta", "").strip()
    sujeito = request.args.get("sujeito", "").strip()
    date_from = date_arg("date_from")
    date_to = date_arg("date_to")
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
        q = q.filter(Booking.slot_date >= date_from)
    if date_to:
        q = q.filter(Booking.slot_date <= date_to)
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

    # Out-of-range numbers are clamped; only non-numbers are rejected.
    page = max(1, int_arg("page", 1, -10**9, 10**9))
    per_page = min(100, max(1, int_arg("per_page", 30, -10**9, 10**9)))
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
    date_from = date_arg("date_from")
    date_to = date_arg("date_to")
    group_by = request.args.get("group_by", "week")
    if group_by not in ("day", "week", "month"):
        group_by = "week"

    q = Booking.query
    if regime in ("presencial", "online"):
        q = q.filter(db.func.lower(Booking.regime) == regime)
    if local:
        q = q.filter(Booking.local_consulta == local)
    if date_from:
        q = q.filter(Booking.slot_date >= date_from)
    if date_to:
        q = q.filter(Booking.slot_date <= date_to)

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


# Everything the admin must supply to create a booking by hand. `contexto` and
# `local_consulta` are optional, and `status` defaults below.
CREATE_REQUIRED = (
    "nome", "email", "contacto", "idade", "sujeito", "tipo_consulta",
    "regime", "slot_date", "slot_time", "duration_minutes", "price",
)

_TEXT_FIELDS = ("nome", "contacto", "sujeito", "tipo_consulta", "regime", "local_consulta", "contexto")
_OPTIONAL_TEXT = ("local_consulta", "contexto")


def _number(value, field, kind, lo, hi):
    if isinstance(value, bool):
        raise BadInput(f"invalid_{field}", field)
    try:
        n = kind(value.strip() if isinstance(value, str) else value)
    except (ValueError, TypeError):
        raise BadInput(f"invalid_{field}", field)
    if not lo <= n <= hi:
        raise BadInput(f"invalid_{field}", field)
    return n


def _clean_fields(data):
    """Validated values for every booking field present (and not null) in `data`.

    Raises BadInput before anything is written, so a rejected edit never
    half-applies. Looser than the public form on purpose: sujeito, tipo_consulta
    and local_consulta stay free text — the modal edits sujeito as text, and older
    bookings hold values the form no longer offers.
    """
    present = {k: v for k, v in data.items() if v is not None}
    out = {}
    for f in _TEXT_FIELDS:
        if f not in present:
            continue
        if not isinstance(present[f], str):
            raise BadInput("invalid_field", f)
        out[f] = present[f].strip() or None
        if out[f] is None and f not in _OPTIONAL_TEXT:
            raise BadInput("empty_field", f)
    if "idade" in present:
        v = present["idade"]
        if isinstance(v, bool) or not isinstance(v, (str, int)) or not str(v).strip():
            raise BadInput("invalid_field", "idade")
        out["idade"] = str(v).strip()
    if "email" in present:
        email = present["email"].strip().lower() if isinstance(present["email"], str) else ""
        if not EMAIL_RE.match(email):
            raise BadInput("invalid_email", "email")
        out["email"] = email

    field = too_long(out, BOOKING_LIMITS)
    if field:
        raise BadInput("field_too_long", field)
    if "regime" in out:
        choice(out, "regime", REGIMES)

    if "status" in present:
        if present["status"] not in STATUSES:
            raise BadInput("invalid_status", "status")
        out["status"] = present["status"]
    if "price" in present:
        out["price"] = _number(present["price"], "price", float, 0, 1000)
    if "duration_minutes" in present:
        out["duration_minutes"] = _number(present["duration_minutes"], "duration_minutes", int, 15, 240)
    if present.get("slot_date"):
        out["slot_date"] = parse_date(present["slot_date"])
    if present.get("slot_time"):
        out["slot_time"] = parse_time(present["slot_time"])
    return out


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
    data = json_body()

    # Emptiness, not falsiness — a price of 0 is a legitimate value.
    missing = [f for f in CREATE_REQUIRED if data.get(f) in (None, "")]
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    fields = _clean_fields({**data, "status": data.get("status") or "confirmado"})
    if fields["regime"].lower() == "online":
        fields["local_consulta"] = None

    booking = Booking(
        reference=generate_unique_reference(),
        sujeito=fields["sujeito"],
        tipo_consulta=fields["tipo_consulta"],
        regime=fields["regime"],
        local_consulta=fields.get("local_consulta"),
        nome=fields["nome"],
        idade=fields["idade"],
        email=fields["email"],
        contacto=fields["contacto"],
        contexto=fields.get("contexto"),
        slot_date=fields["slot_date"],
        slot_time=fields["slot_time"],
        duration_minutes=fields["duration_minutes"],
        price=fields["price"],
        is_first=_parse_is_first(data.get("is_first")),
        status=fields["status"],
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
    booking = Booking.query.filter_by(reference=reference.upper()).first()
    if not booking:
        return jsonify({"error": "not_found"}), 404

    data = json_body()
    # The admin chooses per-save whether the client is emailed the new details.
    notify = bool(data.get("notify", True))
    fields = _clean_fields(data)
    # Moving a booking into confirmado is when a held payment is charged.
    if fields.get("status") == "confirmado" and booking.status != "confirmado":
        try:
            payments.capture(booking)
        except payments.PaymentError as e:
            return jsonify({"error": "capture_failed", "message": str(e)}), 409
    for field, value in fields.items():
        setattr(booking, field, value)
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
    booking = Booking.query.filter_by(reference=reference.upper()).first()
    if not booking:
        return jsonify({"error": "not_found"}), 404
    if booking.status == "cancelado":
        return jsonify({"error": "already_cancelled"}), 400
    # The body is optional; the panel may send {"notify": false, "refund": true, "amount": 20}.
    data = request.get_json(force=True, silent=True)
    data = data if isinstance(data, dict) else {}
    notify = bool(data.get("notify", True))
    refunded = 0
    # A hold is always released: an unconfirmed booking can't keep the client's money.
    if booking.payment_status == "authorized" or data.get("refund"):
        try:
            refunded = payments.release_or_refund(booking, _refund_amount(data))
        except payments.PaymentError as e:
            db.session.rollback()
            return jsonify({"error": "refund_failed", "message": str(e)}), 409
    booking.status = "cancelado"
    booking.updated_at = utcnow()
    db.session.commit()
    if booking.google_event_id:
        calendar_service.delete_event(booking.google_event_id)
    # No nutritionist email: she cancelled it herself, and that template says the client did.
    if notify:
        email_service.send_booking_cancelled_client(booking, refunded)
    return jsonify({"booking": _booking_admin_dict(booking)})


def _refund_amount(data):
    """The amount in a refund request, or None for 'everything left'."""
    if data.get("amount") in (None, ""):
        return None
    return _number(data["amount"], "amount", float, 0.01, 1000)


@admin_bp.route("/bookings/<reference>/refund", methods=["POST"])
@auth.require_admin
def refund_booking_admin(reference):
    """A manual refund of any amount up to what is left, e.g. agreed with a client
    who cancelled inside the notice period."""
    booking = Booking.query.filter_by(reference=reference.upper()).first()
    if not booking:
        return jsonify({"error": "not_found"}), 404
    data = request.get_json(force=True, silent=True)
    data = data if isinstance(data, dict) else {}
    if payments.refundable(booking) <= 0:
        return jsonify({"error": "nothing_to_refund"}), 400
    try:
        refunded = payments.release_or_refund(booking, _refund_amount(data))
    except payments.PaymentError as e:
        db.session.rollback()
        return jsonify({"error": "refund_failed", "message": str(e)}), 409
    booking.updated_at = utcnow()
    db.session.commit()
    if data.get("notify", True):
        email_service.send_refund_client(booking, refunded)
    return jsonify({"booking": _booking_admin_dict(booking), "refunded": float(refunded)})


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
