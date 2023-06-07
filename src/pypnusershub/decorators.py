from functools import wraps

from flask import current_app, redirect
from flask_login import current_user

from werkzeug.exceptions import Forbidden, Unauthorized


def check_auth(
    level,
):
    def _check_auth(view_func):
        @wraps(view_func)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if int(current_user.max_level_profil) < level:
                if "REDIRECT_ON_FORBIDDEN" in current_app.config:
                    return redirect(current_app.config["REDIRECT_ON_FORBIDDEN"])
                raise Forbidden(
                    f"""User {current_user.id_role} is not authorized to to this action. 
                        Required profil level is f{level} """
                )
            return view_func(*args, **kwargs)

        return decorated_view

    return _check_auth
