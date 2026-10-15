from flask import current_app, g
from flask.sessions import SecureCookieSessionInterface

from flask_login import LoginManager
from joserfc.errors import ExpiredTokenError, JoseError

from pypnusershub.db.models import User
from pypnusershub.db.tools import decode_token

from pypnusershub.env import db

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, user_id)


@login_manager.request_loader
def load_user_from_request(request):
    header_name = current_app.config.get("AUTH_TOKEN_HEADER", "Authorization")
    bearer = request.headers.get(header_name, default=None, type=str)
    # Falls back to Authorization: serves both mobile (dedicated header) and
    # web (always Authorization) from one instance. Blank counts as absent.
    if (not bearer or not bearer.strip()) and header_name != "Authorization":
        bearer = request.headers.get("Authorization", default=None, type=str)
    if not bearer:
        return None
    # Tolerates a missing/case-insensitive "Bearer" prefix.
    parts = bearer.strip().split(None, 1)
    if not parts:  # header was whitespace-only
        return None
    jwt = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else parts[0]
    try:
        user_dict = decode_token(jwt)
        user = db.session.get(User, user_dict["id_role"])
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
