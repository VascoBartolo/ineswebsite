"""Request parsing and validation shared by the public and admin booking routes.

Every helper raises BadInput, which app.py turns into a 400 — malformed input
must never surface as a 500.
"""
import re
import unicodedata
from datetime import date, time

from flask import request

# Pragmatic email shape check (not full RFC): non-empty local/domain, one @, a dot
# in the domain. Real deliverability is proven by the confirmation email itself.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Per-field maximum lengths, aligned with the DB columns. Over-limit input is a
# 400, never a 500 from the database.
BOOKING_LIMITS = {
    "sujeito": 20, "tipo_consulta": 100, "regime": 20, "nome": 200,
    "idade": 50, "email": 200, "contacto": 50, "local_consulta": 100, "contexto": 2000,
}

# Mirrors website/src/constants/booking.js — tests/test_validation.py pins the values.
SUJEITOS = ("adulto", "bebé")
REGIMES = ("presencial", "online")
TIPOS_CONSULTA = {
    "adulto": ("consulta de pré-concepção", "consulta na gravidez",
               "consulta no pós-parto", "consulta gestão de peso"),
    "bebé": ("introdução alimentar", "seletividade alimentar", "nutrição pediátrica"),
}
CLINICS = (
    "Clínica Manus (Angra do Heroísmo)",
    "Centro de Psicologia Flávia Bessa (Angra do Heroísmo)",
)
STATUSES = ("pendente", "confirmado", "revisao", "cancelado")


class BadInput(Exception):
    def __init__(self, error, field=None):
        super().__init__(error)
        self.error = error
        self.field = field

    def to_dict(self):
        body = {"error": self.error}
        if self.field:
            body["field"] = self.field
        return body


def _canon(value):
    # NFC so a decomposed "é" from some keyboards still matches "bebé".
    return unicodedata.normalize("NFC", value).strip().lower()


def s(data, key):
    """A string field, stripped, or "" — never raises on null / number / list."""
    v = data.get(key)
    return v.strip() if isinstance(v, str) else ""


def choice(data, key, allowed):
    """The canonical entry of `allowed` matching data[key] case-insensitively."""
    wanted = _canon(s(data, key))
    for option in allowed:
        if _canon(option) == wanted:
            return option
    raise BadInput("invalid_choice", key)


def too_long(data, limits):
    """The first field that exceeds its length cap, or None."""
    for field, limit in limits.items():
        v = data.get(field)
        if v is not None and len(str(v).strip()) > limit:
            return field
    return None


def json_body():
    data = request.get_json(force=True, silent=True)
    if not isinstance(data, dict):
        raise BadInput("invalid_body")
    return data


def int_arg(name, default, lo, hi):
    raw = request.args.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise BadInput(f"invalid_{name}", name)
    if not lo <= value <= hi:
        raise BadInput(f"invalid_{name}", name)
    return value


def parse_date(value, field="slot_date"):
    try:
        return date.fromisoformat(str(value).strip())
    except (ValueError, TypeError):
        raise BadInput(f"invalid_{field}", field)


def parse_time(value, field="slot_time"):
    try:
        hh, mm = str(value).strip().split(":")[:2]
        return time(int(hh), int(mm))
    except (ValueError, TypeError):
        raise BadInput(f"invalid_{field}", field)


def date_arg(name):
    raw = request.args.get(name, "").strip()
    return parse_date(raw, name) if raw else None
