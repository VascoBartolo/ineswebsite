import secrets
import string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()


def utcnow():
    """Naive UTC, matching the existing timezone-less DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False)
    sujeito = db.Column(db.String(20), nullable=False)
    tipo_consulta = db.Column(db.String(100), nullable=False)
    regime = db.Column(db.String(20), nullable=False)
    local_consulta = db.Column(db.String(100))
    nome = db.Column(db.String(200), nullable=False)
    # Free text, not an integer: babies' ages are given in months ("6 meses"),
    # adults' in years. The unit is conveyed by `sujeito` and the form label.
    idade = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    contacto = db.Column(db.String(50), nullable=False)
    contexto = db.Column(db.Text)
    slot_date = db.Column(db.Date, nullable=False, index=True)
    slot_time = db.Column(db.Time, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    # True = primeira consulta, False = consulta de seguimento, NULL = unknown.
    # Nullable on purpose: bookings taken before this column existed cannot all be
    # reconstructed — an online adult consultation costs 50€ and lasts 60 min
    # either way — and writing a guess would be indistinguishable from a fact.
    is_first = db.Column(db.Boolean)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    # Full booking lifecycle in one field:
    #   pendente   — requested, awaiting the nutritionist's approval. HOLDS the slot,
    #                but no Google Calendar event exists yet.
    #   confirmado — approved by the nutritionist; calendar event created. HOLDS the slot.
    #   revisao    — rejected / needs a new time. Does NOT hold the slot.
    #   cancelado  — cancelled by the client. Does NOT hold the slot.
    #   aguarda_pagamento — online request sent to Stripe Checkout. HOLDS the slot
    #                only until hold_expires_at; becomes pendente once paid.
    status = db.Column(db.String(20), default="pendente", nullable=False, index=True)
    google_event_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    # Proof of acceptance of the Terms + Privacy Policy, taken server-side.
    # NULL on admin-created and older bookings.
    terms_accepted_at = db.Column(db.DateTime)
    terms_version = db.Column(db.String(32))

    # Online payment (see payments.py). NULL payment_status = no online payment
    # (presencial, admin-created, or booked before payments existed).
    #   pending    — Checkout open      authorized — card/PayPal held, not charged
    #   paid       — charged            released   — hold cancelled, nothing charged
    #   refunded   — fully refunded     expired    — Checkout abandoned
    payment_status = db.Column(db.String(20))
    payment_method_type = db.Column(db.String(30))
    stripe_session_id = db.Column(db.String(255))
    stripe_payment_intent = db.Column(db.String(255))
    amount_paid = db.Column(db.Numeric(10, 2))
    amount_refunded = db.Column(db.Numeric(10, 2))
    paid_at = db.Column(db.DateTime)
    hold_expires_at = db.Column(db.DateTime)
    # Deadline for the nutritionist to confirm: when a card/PayPal hold lapses,
    # or our own deadline for MB WAY, which is charged at once.
    capture_before = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "reference": self.reference,
            "sujeito": self.sujeito,
            "tipo_consulta": self.tipo_consulta,
            "regime": self.regime,
            "local_consulta": self.local_consulta,
            "nome": self.nome,
            "idade": self.idade,
            "email": self.email,
            "contacto": self.contacto,
            "contexto": self.contexto,
            "slot_date": self.slot_date.isoformat(),
            "slot_time": self.slot_time.strftime("%H:%M"),
            "duration_minutes": self.duration_minutes,
            "is_first": self.is_first,
            "price": float(self.price),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "payment_status": self.payment_status,
            "amount_paid": float(self.amount_paid) if self.amount_paid is not None else None,
            "amount_refunded": float(self.amount_refunded or 0),
        }


class LoginAttempt(db.Model):
    """A failed admin login. Shared by every worker and replica, unlike the
    in-memory rate limiter. A new table, so db.create_all() creates it on boot."""
    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(64), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)


def generate_reference() -> str:
    chars = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(chars) for _ in range(8))
    return f"IB-{token}"


def generate_unique_reference() -> str:
    """A reference no existing booking already holds.

    Lives here rather than in app.py so the public booking form and the admin's
    manual entry cannot drift into two different reference formats.
    """
    reference = generate_reference()
    while Booking.query.filter_by(reference=reference).first():
        reference = generate_reference()
    return reference
