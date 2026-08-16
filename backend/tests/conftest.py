import os
import tempfile
import pytest
from werkzeug.security import generate_password_hash

TEST_PASSWORD = "test-pass-123"

# Bind the test DB to a temporary SQLite FILE before importing app. Flask-SQLAlchemy
# builds the engine at db.init_app() (which runs at app import time) from whatever
# config is present then — config changed afterwards is ignored. Setting DATABASE_URL
# here (before import) makes app.py pick up SQLite at import; load_dotenv() does NOT
# override already-set env vars, so the real .env Postgres DSN is not used. A file-based
# SQLite DB (not ':memory:') is shared across connections, so tables created in the
# fixture are visible to the test client's request connections.
_db_fd, _db_path = tempfile.mkstemp(suffix=".sqlite")
os.close(_db_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _db_path.replace("\\", "/")

# Set admin config env BEFORE importing app so its module-level reads pick these up.
os.environ.setdefault("GOOGLE_CREDENTIALS_FILE", "/nonexistent-so-calendar-is-noop")
os.environ["ADMIN_PASSWORD_HASH"] = generate_password_hash(TEST_PASSWORD)
os.environ["ADMIN_TOKEN_SECRET"] = "unit-test-secret-key"
os.environ["ADMIN_COOKIE_SECURE"] = "false"

from app import app as flask_app  # noqa: E402
from models import db, Booking  # noqa: E402


@pytest.fixture
def app():
    flask_app.config.update(TESTING=True)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def make_booking(**overrides):
    from datetime import date, time
    data = dict(
        reference="IB-TEST0001", sujeito="Bebé", tipo_consulta="Pós-parto",
        regime="online", local_consulta=None, nome="Cliente Teste", idade="3",
        email="cliente@teste.pt", contacto="960000000", contexto=None,
        slot_date=date(2026, 7, 15), slot_time=time(16, 0),
        duration_minutes=60, price=50, status="confirmado",
    )
    data.update(overrides)
    b = Booking(**data)
    db.session.add(b)
    db.session.commit()
    return b
