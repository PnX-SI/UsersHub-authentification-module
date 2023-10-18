from flask import current_app, g
from flask.sessions import SecureCookieSessionInterface

from flask_login import LoginManager
from authlib.jose.errors import ExpiredTokenError, JoseError

from pypnusershub.db.models import User
from pypnusershub.db.tools import decode_token

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@login_manager.request_loader
def load_user_from_request(request):
    bearer = request.headers.get("Authorization", default=None, type=str)
    if bearer:
        jwt = bearer.replace("Bearer ", "")
    else:
        return None
    try:
        user_dict = decode_token(jwt)
        user = User.query.get(user_dict["id_role"])
        g.login_via_request = True
        return user
    except (ExpiredTokenError, JoseError):
        return None


class CustomSessionInterface(SecureCookieSessionInterface):
    """Prevent creating session from API requests."""

    def save_session(self, *args, **kwargs):
        if g.get("login_via_request"):
            return
        return super(CustomSessionInterface, self).save_session(*args, **kwargs)
