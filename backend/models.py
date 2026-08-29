from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


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
    price = db.Column(db.Numeric(10, 2), nullable=False)
    # Full booking lifecycle in one field:
    #   pendente   — requested, awaiting the nutritionist's approval. HOLDS the slot,
    #                but no Google Calendar event exists yet.
    #   confirmado — approved by the nutritionist; calendar event created. HOLDS the slot.
    #   revisao    — rejected / needs a new time. Does NOT hold the slot.
    #   cancelado  — cancelled by the client. Does NOT hold the slot.
    status = db.Column(db.String(20), default="pendente", nullable=False, index=True)
    google_event_id = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
            "price": float(self.price),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
