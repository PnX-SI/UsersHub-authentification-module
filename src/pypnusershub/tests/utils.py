from contextlib import contextmanager

from flask import current_app
from werkzeug.http import dump_cookie
from werkzeug.datastructures import Headers

from flask_login import login_user, logout_user
from sqlalchemy import select

from pypnusershub.utils import get_current_app_id
from pypnusershub.db.models import User
from pypnusershub.db.tools import user_to_token
from pypnusershub.env import db


def set_logged_user(client, user):
    user = db.session.execute(
        select(User).filter_by(
            id_role=user.id_role,
        )
    ).scalar_one()
    login_user(user)
    client.environ_base["HTTP_AUTHORIZATION"] = "Bearer " + user_to_token(user).decode()


# retro compatibility for cookie auth
set_logged_user_cookie = set_logged_user


def unset_logged_user(client):
    logout_user()
    client.environ_base.pop("HTTP_AUTHORIZATION")


@contextmanager
def logged_user(client, user):
    """
    Usage:

        with logged_user(client, user):
            response = client.get(url)
    """
    set_logged_user(client, user)
    yield
    unset_logged_user(client)


# retro compatibility for cookie auth
unset_logged_user_cookie = unset_logged_user


def logged_user_headers(user, headers=None):
    user = db.session.execute(
        select(User).filter_by(
            id_role=user.id_role,
        )
    ).scalar_one()
    login_user(user)
    token = user_to_token(user).decode("latin1")
    if headers is None:
        headers = Headers()
    headers.extend(
        {
            "Authorization": f"Bearer {token}",
        }
    )
    return headers
