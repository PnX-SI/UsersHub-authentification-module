import pytest

from flask import Flask

from utils_flask_sqla.tests.utils import JSONClient

from pypnusershub.env import db, ma
from pypnusershub.login_manager import login_manager
from pypnusershub.auth.auth_manager import auth_manager


@pytest.fixture(scope="session", autouse=True)
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

    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def _session(_app):
    return db.session


@pytest.fixture(scope="session", autouse=True)
def app(_app, _session):
    return _app
