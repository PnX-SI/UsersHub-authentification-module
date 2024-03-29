from typing import Any, Union
import json
import logging

import datetime
from flask import (
    request,
    Response,
    current_app,
)
from markupsafe import escape

from sqlalchemy.orm import exc
import sqlalchemy as sa
from werkzeug.exceptions import BadRequest

from pypnusershub.utils import get_current_app_id
from pypnusershub.db import models, db
from pypnusershub.db.tools import (
    encode_token,
)
from pypnusershub.schemas import OrganismeSchema, UserSchema

log = logging.getLogger(__name__)


class Authentification:
    """
    Abstract class for authentication implementations.
    """

    def authenticate(self, *args, **kwargs) -> Union[Response, models.User]:
        """
        Authenticate a user with the provided parameters.

        Parameters
        ----------
        *args : Any
            Positional arguments to be passed to the implementation.
        **kwargs : Any
            Keyword arguments to be passed to the implementation.

        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses.

        Returns
        -------
        Union[Response, models.User]
            The result of the authentication process, which can be either a Response object or a User object.
        """
        raise NotImplementedError()

    def revoke(self) -> Any:
        """
        Revoke current authentication.

        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses.

        Returns
        -------
        Any
            Revocation result depending on the implementation.
        """
        raise NotImplementedError()


class DefaultConfiguration(Authentification):

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
            user_dict = UserSchema(
                exclude=["remarques"], only=["+max_level_profil"]
            ).dump(user)
        except exc.NoResultFound as e:
            msg = json.dumps(
                {
                    "type": "login",
                    "msg": (
                        'No user found with the username "{login}" for '
                        'the application with id "{id_app}"'
                    ).format(login=escape(username), id_app=id_app),
                }
            )
            log.info(msg)
            status_code = current_app.config.get("BAD_LOGIN_STATUS_CODE", 490)
            return Response(msg, status=status_code)

        if not user.check_password(user_data["password"]):
            msg = json.dumps({"type": "password", "msg": "Mot de passe invalide"})
            log.info(msg)
            status_code = current_app.config.get("BAD_LOGIN_STATUS_CODE", 490)
            return Response(msg, status=status_code)
        # Génération d'un token
        token = encode_token(user_dict)
        token_exp = datetime.datetime.now(datetime.timezone.utc)
        token_exp += datetime.timedelta(seconds=current_app.config["COOKIE_EXPIRATION"])
        return user

    def revoke(self) -> Any:
        pass
