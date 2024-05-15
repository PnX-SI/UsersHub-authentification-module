import json
from typing import Any, Union

import sqlalchemy as sa
from flask import Response, request
from pypnusershub.db import db, models
from pypnusershub.utils import get_current_app_id
from sqlalchemy.orm import exc
from werkzeug.exceptions import BadRequest, Unauthorized

from ..authentication import Authentication


class DefaultConfiguration(Authentication):
    login_url = ""
    logout_url = ""
    id_provider = "local_provider"

    def authenticate(self, *args, **kwargs) -> Union[Response, models.User]:
        user_data = request.json
        try:
            username, password = user_data.get("login"), user_data.get("password")
            id_app = user_data.get("id_application", get_current_app_id())

            if id_app is None or username is None or password is None:
                msg = json.dumps(
                    "One of the following parameter is required ['id_application', 'login', 'password']"
                )
                return Response(msg, status=400)
            app = db.session.get(models.Application, id_app)
            if not app:
                raise BadRequest(f"No app for id {id_app}")
            user = db.session.execute(
                sa.select(models.User)
                .where(models.User.identifiant == username)
                .where(models.User.filter_by_app())
            ).scalar_one()
        except exc.NoResultFound as e:
            raise Unauthorized(
                'No user found with the username "{login}" for the application with id "{id_app}"'
            )

        if not user.check_password(user_data["password"]):
            raise Unauthorized("Invalid password")
        return user

    def revoke(self) -> Any:
        pass
