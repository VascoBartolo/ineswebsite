import time
from flask import Blueprint, request, jsonify

import auth

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


@admin_bp.route("/bookings")
@auth.require_admin
def list_bookings():
    # Stub only — replaced with the real query in Task 5. Present now so the
    # auth guard test (401 without cookie) passes.
    return jsonify({"bookings": [], "summary": {}})
