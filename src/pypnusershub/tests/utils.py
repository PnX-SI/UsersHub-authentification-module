from flask import current_app
from werkzeug.http import dump_cookie
from werkzeug.datastructures import Headers

from pypnusershub.db.models import AppUser
from pypnusershub.db.tools import user_to_token


def set_logged_user_cookie(client, user):
    app_user = AppUser.query.filter_by(
                                id_role=user.id_role,
                                id_application=current_app.config['ID_APP'],
    ).one()
    client.set_cookie(current_app.config['SERVER_NAME'], 'token', user_to_token(app_user))


def unset_logged_user_cookie(client):
    client.delete_cookie(current_app.config['SERVER_NAME'], 'token')


def logged_user_headers(user, headers=None):
    app_user = AppUser.query.filter_by(
                                id_role=user.id_role,
                                id_application=current_app.config['ID_APP'],
    ).one()
    token = user_to_token(app_user).decode("latin1")
    if headers is None:
        headers = Headers()
    headers.extend({
        'Cookie': f'token={token}',
    })
    return headers
