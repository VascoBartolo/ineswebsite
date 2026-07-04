import time
import pytest
from conftest import TEST_PASSWORD
import auth


def test_verify_password_correct(app):
    with app.app_context():
        assert auth.verify_password(TEST_PASSWORD) is True


def test_verify_password_wrong(app):
    with app.app_context():
        assert auth.verify_password("nope") is False


def test_token_roundtrip(app):
    with app.app_context():
        token = auth.issue_token()
        assert auth.verify_token(token) is True


def test_token_tampered_rejected(app):
    with app.app_context():
        token = auth.issue_token()
        assert auth.verify_token(token + "x") is False


def test_token_expired_rejected(app):
    with app.app_context():
        token = auth.issue_token()
        # Valid within a normal window...
        assert auth.verify_token(token, max_age=3600) is True
        # ...but rejected once older than max_age. Sleep 1s so age (>=1) exceeds
        # max_age=0 (itsdangerous treats age 0 as still valid: it checks age > max_age).
        time.sleep(1)
        assert auth.verify_token(token, max_age=0) is False


def test_verify_none_token(app):
    with app.app_context():
        assert auth.verify_token(None) is False
