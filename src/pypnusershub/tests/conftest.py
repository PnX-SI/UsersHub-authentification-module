import pytest

from flask import Flask, request

from utils_flask_sqla.tests.utils import JSONClient

from pypnusershub.env import db, ma
from utils_flask_sqla.tests.utils import TestSession
from pypnusershub.login_manager import login_manager
from pypnusershub.auth.auth_manager import auth_manager
from .fixtures import *

db.session = db._make_scoped_session({"class_": TestSession})


@pytest.fixture(scope="session")
def _app():
    app = Flask("pypnusershub")
    from pypnusershub.routes import routes

    app.testing = True
    app.test_client_class = JSONClient
    app.config.from_envvar("USERSHUB_AUTH_MODULE_SETTINGS")
    app.testing = True
    db.init_app(app)
    ma.init_app(app)
    auth_manager.init_app(
        app, providers_declaration=app.config["AUTHENTICATION"]["PROVIDERS"]
    )
    login_manager.init_app(app)

    @app.before_request
    def get_endpoint():
        pytest.endpoint = request.endpoint

    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def _session(_app):
    return db.session


@pytest.fixture(scope="session", autouse=True)
def app(_app, _session):
    return _app
