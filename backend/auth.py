import time
from functools import wraps

from flask import current_app, request, jsonify
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash

COOKIE_NAME = "admin_token"
COOKIE_PATH = "/api/admin"
TOKEN_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
_SALT = "ib-admin-session"

# Small fixed delay on failed logins to blunt brute-force.
LOGIN_FAIL_DELAY = 0.4


def _serializer():
    secret = current_app.config.get("ADMIN_TOKEN_SECRET") or ""
    return URLSafeTimedSerializer(secret, salt=_SALT)


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
