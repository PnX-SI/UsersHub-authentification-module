import time
from contextlib import contextmanager

import pytest
from flask import current_app, request as flask_request
from joserfc import jwk as joserfc_jwk
from joserfc import jwt as joserfc_jwt

from pypnusershub.db.models import User
from pypnusershub.db.tools import encode_token
from pypnusershub.env import db
from pypnusershub.login_manager import load_user_from_request
from .fixtures import *


@pytest.fixture()
def existing_user(app):
    with db.session.begin_nested():
        user = User(groupe=False, identifiant="login.manager.test.user")
        db.session.add(user)
    return user


def token_for(user):
    return encode_token({"id_role": user.id_role})


@contextmanager
def auth_token_header(app, header_name):
    app.config["AUTH_TOKEN_HEADER"] = header_name
    try:
        yield
    finally:
        app.config.pop("AUTH_TOKEN_HEADER", None)


def test_default_header(app, existing_user):
    token = token_for(existing_user)
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        user = load_user_from_request(flask_request)
    assert user.id_role == existing_user.id_role


def test_custom_header(app, existing_user):
    token = token_for(existing_user)
    with auth_token_header(app, "X-GN-Token"):
        with app.test_request_context(headers={"X-GN-Token": f"Bearer {token}"}):
            user = load_user_from_request(flask_request)
    assert user.id_role == existing_user.id_role


def test_custom_header_fallback(app, existing_user):
    # Plain web clients only ever send Authorization, no reconfiguring needed.
    token = token_for(existing_user)
    with auth_token_header(app, "X-GN-Token"):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            user = load_user_from_request(flask_request)
    assert user.id_role == existing_user.id_role


def test_bearer_prefix_is_case_insensitive(app, existing_user):
    token = token_for(existing_user)
    with app.test_request_context(headers={"Authorization": f"bearer {token}"}):
        user = load_user_from_request(flask_request)
    assert user.id_role == existing_user.id_role


def test_tolerates_missing_bearer_prefix(app, existing_user):
    token = token_for(existing_user)
    with app.test_request_context(headers={"Authorization": token}):
        user = load_user_from_request(flask_request)
    assert user.id_role == existing_user.id_role


def test_missing_header(app):
    with app.test_request_context():
        assert load_user_from_request(flask_request) is None


def test_whitespace_only_header(app):
    with app.test_request_context(headers={"Authorization": "   "}):
        assert load_user_from_request(flask_request) is None


def test_garbage_token(app):
    with app.test_request_context(headers={"Authorization": "Bearer not-a-real-jwt"}):
        assert load_user_from_request(flask_request) is None


def test_expired_token(app, existing_user):
    key = joserfc_jwk.import_key(
        current_app.config["SECRET_KEY"].encode("UTF-8"), "oct"
    )
    token = joserfc_jwt.encode(
        {"alg": "HS256"},
        {"id_role": existing_user.id_role, "exp": int(time.time()) - 3600},
        key,
    )
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        assert load_user_from_request(flask_request) is None
