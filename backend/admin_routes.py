import time
from datetime import date as _date
from flask import Blueprint, request, jsonify

import auth
from models import db, Booking
import stats as stats_mod

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
    return d


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

    if status in ("confirmado", "cancelado"):
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
        like = f"%{search}%"
        q = q.filter(db.or_(
            db.func.lower(Booking.nome).like(like),
            db.func.lower(Booking.email).like(like),
            db.func.lower(Booking.reference).like(like),
        ))

    rows = q.order_by(Booking.slot_date.desc(), Booking.slot_time.desc()).all()
    bookings = [_booking_admin_dict(b) for b in rows]
    confirmed = [b for b in rows if b.status == "confirmado"]
    summary = {
        "count": len(rows),
        "confirmed_count": len(confirmed),
        "faturado": round(sum(float(b.price) for b in confirmed), 2),
    }
    return jsonify({"bookings": bookings, "summary": summary})


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
