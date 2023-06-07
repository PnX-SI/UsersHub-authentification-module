import pytest

from flask import Flask

from utils_flask_sqla.tests.utils import JSONClient

from pypnusershub.env import db, ma
from pypnusershub.login_manager import login_manager


@pytest.fixture(scope="session", autouse=True)
def app():
    app = Flask("pypnusershub")
    from pypnusershub.routes import routes

    app.register_blueprint(routes)
    app.testing = True
    app.test_client_class = JSONClient

    app.config.from_envvar("USERSHUB_AUTH_MODULE_SETTINGS")
    app.testing = True
    db.init_app(app)
    ma.init_app(app)
    login_manager.init_app(app)
    with app.app_context():
        transaction = db.session.begin_nested()  # execute tests in a savepoint
        yield app
        transaction.rollback()  # rollback all database changes


@pytest.fixture(scope="session")
def _session(app):
    return db.session
