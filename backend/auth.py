import time
from functools import wraps

from flask import current_app, request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash

COOKIE_NAME = "admin_token"
COOKIE_PATH = "/api/admin"
TOKEN_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
_SALT = "ib-admin-session"

# Booking-action links in the nutritionist's email are clicked without a login
# session, so each link carries a signed, time-limited token that binds the booking
# reference to a single action. The signature (over ADMIN_TOKEN_SECRET) is the
# authorization: unguessable, tamper-evident and expiring. A distinct salt keeps
# these tokens from ever being accepted as admin-session cookies.
_BOOKING_ACTION_SALT = "ib-booking-action"
BOOKING_ACTION_MAX_AGE = 60 * 60 * 24 * 45  # 45 days
BOOKING_ACTIONS = ("confirm", "revise")

# Small fixed delay on failed logins to blunt brute-force.
LOGIN_FAIL_DELAY = 0.4


def _serializer():
    secret = current_app.config.get("ADMIN_TOKEN_SECRET") or ""
    return URLSafeTimedSerializer(secret, salt=_SALT)


def _booking_action_serializer():
    secret = current_app.config.get("ADMIN_TOKEN_SECRET") or ""
    return URLSafeTimedSerializer(secret, salt=_BOOKING_ACTION_SALT)


def sign_booking_action(reference, action):
    """Signed token authorizing `action` on the booking `reference`."""
    if action not in BOOKING_ACTIONS:
        raise ValueError(f"unknown booking action: {action}")
    return _booking_action_serializer().dumps({"ref": reference, "action": action})


def verify_booking_action(token, max_age=BOOKING_ACTION_MAX_AGE):
    """Return {"ref", "action"} for a valid token, else None."""
    if not token:
        return None
    try:
        data = _booking_action_serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, dict):
        return None
    ref, action = data.get("ref"), data.get("action")
    if not ref or action not in BOOKING_ACTIONS:
        return None
    return {"ref": ref, "action": action}


def verify_password(password):
    stored = current_app.config.get("ADMIN_PASSWORD_HASH") or ""
    if not stored or not password:
        return False
    return check_password_hash(stored, password)


def issue_token():
    return _serializer().dumps({"role": "admin"})


def verify_token(token, max_age=TOKEN_MAX_AGE):
    if not token:
        return False
    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return False
    return data.get("role") == "admin"


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.cookies.get(COOKIE_NAME)
        if not verify_token(token):
            return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


def set_auth_cookie(response, token):
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=TOKEN_MAX_AGE, path=COOKIE_PATH,
        httponly=True, secure=current_app.config.get("ADMIN_COOKIE_SECURE", True),
        samesite="Strict",
    )
    return response


def clear_auth_cookie(response):
    response.set_cookie(
        COOKIE_NAME, "", max_age=0, path=COOKIE_PATH,
        httponly=True, secure=current_app.config.get("ADMIN_COOKIE_SECURE", True),
        samesite="Strict",
    )
    return response
