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
from werkzeug.exceptions import Unauthorized

log = logging.getLogger(__name__)


class AuthenticationMeta:
    pass

    # def __instancecheck__(cls, instance):
    #     return cls.__subclasscheck__(type(instance))

    # def __subclasscheck__(cls, subclass):
    #     return all([hasattr(subclass, field) for field in cls.required_fields])


class Authentication:
    """
    Abstract class for authentication implementations.
    """

    @property
    def id_provider(self) -> str:
        """
        Identifier of the authentication provider.

        Returns
        -------
        str
            The authentication provider identifier.

        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses.
        """
        raise NotImplementedError()

    @property
    def label(self) -> str:
        """
        Label of the authentication provider.

        Returns
        -------
        str
            The label of the authentication provider.
        """

    @property
    def login_url(self) -> str:
        """
        External logout URL.
        Must be define if the authentication provider is external, otherwise put an empty string
        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses.
        """
        raise NotImplementedError()

    @property
    def logout_url(self) -> str:
        """
        External logout URL.
        Must be define if the authentication provider is external, otherwise put an empty string

        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses.
        """
        raise NotImplementedError()

    @property
    def logo(self) -> str:
        """
        Logo of the authentication provider.

        Returns
        -------
        str
            URL of the logo image.
        """
        return ""

    @property
    def is_uh(self) -> bool:
        """
        Return whether the authentication is an 'usershub-auth-module' authentication.

        Returns
        -------
        bool
        """
        return True

    def authenticate(self, *args, **kwargs) -> models.User:
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
        models.User
            The result of the authentication process, which must be a User object.
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

    def authorize(self) -> Any:
        raise NotImplementedError()


class DefaultConfiguration(Authentication):
    login_url = ""
    logout_url = ""
    id_provider = "default"

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
