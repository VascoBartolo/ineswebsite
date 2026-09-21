import logging
import os
from calendar import monthrange
from datetime import datetime, date, timedelta

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import text
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("ibnutricao")

from models import db, Booking, generate_unique_reference, utcnow
import calendar_service
import email_service
from validation import (
    BOOKING_LIMITS, CLINICS, EMAIL_RE, REGIMES, SUJEITOS, TIPOS_CONSULTA,
    BadInput, choice, int_arg, json_body, parse_date, parse_time, s, too_long,
)

load_dotenv()

app = Flask(__name__)

# Behind the ACA ingress + nginx, the caller's IP arrives in X-Forwarded-For.
# Without this, request.remote_addr is the proxy, so rate limiting and request
# logging key on the proxy (one shared bucket) instead of the real client.
# x_for=3 verified empirically against the live chain (2026-08-16): the request
# passes through three trusted proxies — frontend ACA ingress, frontend nginx,
# backend ACA ingress — which append exactly three entries, so the real client
# IP sits at position -3. Client-supplied X-Forwarded-For entries stay to the
# left of those three, so this cannot be spoofed.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=3, x_proto=1)

allowed_origins = [os.environ.get("FRONTEND_URL", "")]
if os.environ.get("CORS_ALLOW_LOCALHOST", "false").lower() == "true":
    allowed_origins += ["http://localhost:5173", "http://localhost:3000"]
CORS(app, origins=[o for o in allowed_origins if o])

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per minute"],
    storage_uri="memory://",
)

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "postgresql://ibnutricao:ibnutricao@localhost:5432/ibnutricao",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["ADMIN_PASSWORD_HASH"] = os.environ.get("ADMIN_PASSWORD_HASH", "")
app.config["ADMIN_TOKEN_SECRET"] = os.environ.get("ADMIN_TOKEN_SECRET", "")
app.config["ADMIN_COOKIE_SECURE"] = os.environ.get("ADMIN_COOKIE_SECURE", "true").lower() == "true"
# Cap request bodies so an oversized payload can't exhaust memory. Bookings and
# contact messages are small; 64 KB is generous. Over-limit -> 413.
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

# An empty secret would sign admin sessions and email action links with a known key.
for _key in ("ADMIN_TOKEN_SECRET", "ADMIN_PASSWORD_HASH"):
    if not app.config[_key]:
        raise RuntimeError(f"{_key} must be set")
if len(app.config["ADMIN_TOKEN_SECRET"]) < 32:
    raise RuntimeError("ADMIN_TOKEN_SECRET must be at least 32 characters")

db.init_app(app)

from admin_routes import admin_bp
app.register_blueprint(admin_bp)

from booking_action_routes import booking_action_bp
app.register_blueprint(booking_action_bp)

limiter.limit("5 per minute")(app.view_functions["admin.login"])
# Booking-action links are clicked by the nutritionist from email; keep them usable
# but bounded against abuse of the (signed) endpoints.
limiter.limit("30 per minute")(app.view_functions["booking_action.action_page"])
limiter.limit("30 per minute")(app.view_functions["booking_action.action_execute"])


@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "bad_request"}), 400

@app.errorhandler(BadInput)
def bad_input(e):
    return jsonify(e.to_dict()), 400

@app.errorhandler(404)
def not_found_error(e):
    return jsonify({"error": "not_found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "method_not_allowed"}), 405

@app.errorhandler(413)
def payload_too_large(e):
    return jsonify({"error": "payload_too_large"}), 413

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "rate_limited", "message": "Demasiados pedidos. Tente novamente mais tarde."}), 429

@app.errorhandler(500)
def internal_error(e):
    logger.exception("Unhandled exception")
    return jsonify({"error": "internal_error"}), 500


@app.after_request
def security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


@app.after_request
def log_request(response):
    logger.info("%s %s %s %s", request.method, request.path, response.status_code, request.remote_addr)
    return response


# ---- Business logic ----


def compute_price(is_first: bool, regime: str) -> float:
    """
    Presencial: primeira=55€, seguimento=50€
    Online:     always 50€ regardless of first/following
    """
    if regime.lower() == "presencial":
        return 55.0 if is_first else 50.0
    return 50.0


def compute_duration(sujeito: str, is_first: bool) -> int:
    """Babies' first consultation is 90 min; everything else is 60 min."""
    if sujeito.lower() == "bebé" and is_first:
        return 90
    return 60


def db_busy_intervals_range(start_date, end_date):
    """Confirmed DB bookings in [start_date, end_date] bucketed by date, as event
    dicts compatible with calendar_service. One query for the whole range."""
    bookings = Booking.query.filter(
        Booking.slot_date >= start_date,
        Booking.slot_date <= end_date,
        # Pending requests hold the slot too — not only nutritionist-approved ones.
        Booking.status.in_(["pendente", "confirmado"]),
    ).all()
    buckets = {}
    for b in bookings:
        start = datetime.combine(b.slot_date, b.slot_time)
        end = start + timedelta(minutes=int(b.duration_minutes))
        buckets.setdefault(b.slot_date, []).append({
            "start_dt": start,
            "end_dt": end,
            "location": (b.regime.lower(), b.local_consulta),
        })
    return buckets


def db_busy_intervals(query_date):
    """Returns DB bookings as event dicts compatible with calendar_service."""
    return db_busy_intervals_range(query_date, query_date).get(query_date, [])


# ---- Routes ----

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/availability")
def availability():
    date_str = request.args.get("date", "").strip()
    duration = int_arg("duration", 60, 30, 180)
    regime = request.args.get("regime", "").strip().lower() or None
    local_consulta = request.args.get("local_consulta", "").strip() or None

    if not date_str:
        return jsonify({"error": "date required"}), 400

    try:
        query_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "invalid date"}), 400

    if query_date < calendar_service.now_azores().date():
        return jsonify({"slots": [], "date": date_str})

    new_location = (regime, local_consulta) if regime else None
    all_events = db_busy_intervals(query_date) + calendar_service.get_gcal_events(query_date)
    slots = calendar_service.get_available_slots(query_date, duration, all_events, new_location)
    return jsonify({"slots": slots, "date": date_str})


@app.route("/api/availability/month")
def availability_month():
    """
    Number of free slots for every day of a month, so the booking calendar can
    show availability at a glance. Deliberately batched: ONE Google Calendar
    fetch and ONE DB query for the whole month, not one per day.
    """
    year = int_arg("year", None, 2020, 2100)
    month = int_arg("month", None, 1, 12)
    if year is None or month is None:
        return jsonify({"error": "year and month required"}), 400

    duration = int_arg("duration", 60, 30, 180)
    regime = request.args.get("regime", "").strip().lower() or None
    local_consulta = request.args.get("local_consulta", "").strip() or None
    new_location = (regime, local_consulta) if regime else None

    first = date(year, month, 1)
    last = date(year, month, monthrange(year, month)[1])

    gcal_by_day = calendar_service.get_gcal_events_range(first, last)
    db_by_day = db_busy_intervals_range(first, last)

    today = calendar_service.now_azores().date()
    days = {}
    current = first
    while current <= last:
        if current < today:
            days[current.isoformat()] = 0
        else:
            events = db_by_day.get(current, []) + gcal_by_day.get(current, [])
            days[current.isoformat()] = len(
                calendar_service.get_available_slots(current, duration, events, new_location)
            )
        current += timedelta(days=1)

    return jsonify({"year": year, "month": month, "days": days})


@app.route("/api/bookings", methods=["POST"])
@limiter.limit("10 per minute")
def create_booking():
    data = json_body()

    idade = data.get("idade")
    idade = str(idade).strip() if isinstance(idade, (str, int)) and not isinstance(idade, bool) else ""
    values = {f: s(data, f) for f in ("sujeito", "tipo_consulta", "regime", "nome", "email", "contacto")}
    values["idade"] = idade
    required = ["sujeito", "tipo_consulta", "regime", "nome", "idade", "email", "contacto", "slot_date", "slot_time"]
    missing = [f for f in required if not (values[f] if f in values else data.get(f))]
    if missing:
        return jsonify({"error": f"missing fields: {', '.join(missing)}"}), 400

    field = too_long(data, BOOKING_LIMITS)
    if field:
        return jsonify({"error": "field_too_long", "field": field}), 400
    if not EMAIL_RE.match(values["email"]):
        return jsonify({"error": "invalid_email", "message": "Email inválido."}), 400

    # Price and duration derive from these, so only the options the form offers are accepted.
    sujeito = choice(data, "sujeito", SUJEITOS)
    regime = choice(data, "regime", REGIMES)
    tipo_consulta = choice(data, "tipo_consulta", TIPOS_CONSULTA[sujeito])
    local_consulta_val = choice(data, "local_consulta", CLINICS) if regime == "presencial" else None

    is_first = data.get("is_first", True)
    if not isinstance(is_first, bool):
        raise BadInput("invalid_is_first", "is_first")

    slot_date = parse_date(data["slot_date"])
    slot_time = parse_time(data["slot_time"])

    price = compute_price(is_first, regime)
    duration = compute_duration(sujeito, is_first)
    new_location = (regime, local_consulta_val)

    # Serialize concurrent bookings for the same day so the availability check and the
    # insert below can't interleave into a double-booking (TOCTOU). Transaction-scoped
    # advisory lock: auto-released on commit/rollback and shared across all replicas.
    # Postgres only — a harmless no-op on SQLite (tests).
    if db.engine.dialect.name == "postgresql":
        db.session.execute(text("SELECT pg_advisory_xact_lock(:k)"),
                           {"k": int(slot_date.strftime("%Y%m%d"))})

    # Confirm slot still available
    all_events = db_busy_intervals(slot_date) + calendar_service.get_gcal_events(slot_date)
    available = calendar_service.get_available_slots(slot_date, duration, all_events, new_location)
    if slot_time.strftime("%H:%M") not in available:
        return jsonify({"error": "slot_unavailable", "message": "Este horário já não está disponível. Por favor escolha outro."}), 409

    reference = generate_unique_reference()

    booking = Booking(
        reference=reference,
        sujeito=sujeito,
        tipo_consulta=tipo_consulta,
        regime=regime,
        local_consulta=local_consulta_val,
        nome=values["nome"],
        idade=values["idade"],
        email=values["email"].lower(),
        contacto=values["contacto"],
        contexto=s(data, "contexto") or None,
        slot_date=slot_date,
        slot_time=slot_time,
        duration_minutes=duration,
        price=price,
        is_first=is_first,
        status="pendente",
    )

    db.session.add(booking)
    db.session.commit()

    # NB: no Google Calendar event is created here. The event is created only when
    # the nutritionist approves the request (see booking_action_routes.action_execute).
    # The slot is still held meanwhile because pending bookings count as busy.

    # Email notifications. The client is told the slot is reserved and awaiting the
    # nutritionist's confirmation ("Consulta Marcada"); she confirms/revises from the
    # action buttons in her own notification email.
    email_service.send_booking_received_client(booking)
    email_service.send_nutritionist_new_booking(booking)

    return jsonify({"booking": booking.to_dict()}), 201


@app.route("/api/contact", methods=["POST"])
@limiter.limit("5 per minute")
def contact():
    data = json_body()
    name = s(data, "name")
    email = s(data, "email").lower()
    subject = s(data, "subject")
    message = s(data, "message")

    if not name or not email or not subject or not message:
        return jsonify({"error": "missing fields"}), 400
    if len(name) > 200 or len(email) > 200 or len(subject) > 200 or len(message) > 5000:
        return jsonify({"error": "field_too_long"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "invalid_email", "message": "Email inválido."}), 400

    phone = s(data, "phone")[:50]
    email_service.send_contact_message(name, email, phone, subject, message)
    return jsonify({"message": "sent"}), 200


@app.route("/api/bookings/lookup", methods=["POST"])
@limiter.limit("20 per minute")
def lookup():
    # POST body, not query string: a URL carrying the client's email ends up in
    # proxy access logs and browser history.
    data = json_body()
    reference = s(data, "reference").upper()
    email = s(data, "email").lower()

    if not reference or not email:
        return jsonify({"error": "reference and email required"}), 400

    booking = Booking.query.filter(
        Booking.reference == reference,
        db.func.lower(Booking.email) == email,
    ).first()

    if not booking:
        return jsonify({"error": "not_found", "message": "Marcação não encontrada."}), 404

    return jsonify({"booking": booking.to_dict()})


@app.route("/api/bookings/<reference>/cancel", methods=["PUT"])
@limiter.limit("20 per minute")
def cancel_booking(reference):
    data = json_body()
    email = s(data, "email").lower()

    booking = Booking.query.filter(
        Booking.reference == reference.upper(),
        db.func.lower(Booking.email) == email,
    ).first()

    if not booking:
        return jsonify({"error": "not_found"}), 404
    if booking.status == "cancelado":
        return jsonify({"error": "already_cancelled"}), 400

    slot_dt = datetime.combine(booking.slot_date, booking.slot_time)
    if slot_dt < calendar_service.now_azores():
        return jsonify({"error": "past_booking", "message": "Não é possível cancelar uma consulta passada."}), 400

    booking.status = "cancelado"
    booking.updated_at = utcnow()
    db.session.commit()

    if booking.google_event_id:
        calendar_service.delete_event(booking.google_event_id)

    email_service.send_booking_cancelled_client(booking)
    email_service.send_nutritionist_cancellation(booking)

    return jsonify({"message": "cancelled", "booking": booking.to_dict()})


@app.route("/api/bookings/<reference>/edit-request", methods=["PUT"])
@limiter.limit("20 per minute")
def edit_request(reference):
    data = json_body()
    email = s(data, "email").lower()
    message = s(data, "message")

    if not message:
        return jsonify({"error": "message required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "field_too_long", "field": "message"}), 400

    booking = Booking.query.filter(
        Booking.reference == reference.upper(),
        db.func.lower(Booking.email) == email,
    ).first()

    if not booking:
        return jsonify({"error": "not_found"}), 404
    if booking.status == "cancelado":
        return jsonify({"error": "booking_cancelled"}), 400

    email_service.send_nutritionist_edit_request(booking, message)
    return jsonify({"message": "edit_request_sent"})


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
            host="0.0.0.0", port=5000)
