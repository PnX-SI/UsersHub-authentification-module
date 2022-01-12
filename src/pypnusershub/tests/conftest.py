import pytest

from flask import Flask
from pypnusershub.env import db, ma


@pytest.fixture(scope='session', autouse=True)
def app():
    app = Flask('pypnusershub')
    app.config.from_envvar('USERSHUB_AUTH_MODULE_SETTINGS') 
    app.testing = True
    db.init_app(app)
    ma.init_app(app)
    with app.app_context():
        transaction = db.session.begin_nested()  # execute tests in a savepoint
        yield app
        transaction.rollback()  # rollback all database changes

@pytest.fixture(scope='session')
def _session(app):
    return db.session
