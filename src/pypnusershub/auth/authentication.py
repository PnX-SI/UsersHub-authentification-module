from typing import Any, Optional, Tuple, Union
import json
import logging

import datetime
from flask import (
    request,
    Response,
    current_app,
)
import warnings

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

from marshmallow import Schema, fields

log = logging.getLogger(__name__)


class ProviderConfigurationSchema(Schema):
    id_provider = fields.Str(required=True)


class Authentication:
    """
    Abstract class for authentication implementations.
    """

    @property
    def name(self) -> str:
        """
        Name of the authentication provider.
        Use for config key

        Returns
        -------
        str
            The name of the authentication provider.
        """
        raise NotImplementedError()

    """Identifier of the instance of the authentication provider.
    Is override by provider config config
    Returns
    -------
    str
        The authentication provider identifier."""
    id_provider = None

    @property
    def label(self) -> str:
        """
        Label of the authentication provider.
        Use in frontend
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

    def authorize(self) -> Any:
        """
        Authorize the current user.

        This function is meant to be called after a successful authentication (`/login`)
        in order to complete the authorization process. It will reconcile the data recovered
        from the login provider and the database. It will return a User object
        or raise an exception if the authorization process fails.

        Returns
        -------
        Any
            A redirect response or an exception.

        Raises
        ------
        NotImplementedError
            This method must be implemented by subclasses.
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
        log.warn("Revoke is not implemented.")
        pass

    def configure(self, configuration: Union[dict, Any] = {}):
        self.id_provider = configuration["id_provider"]

    @staticmethod
    def configuration_schema() -> ProviderConfigurationSchema:
        return ProviderConfigurationSchema
