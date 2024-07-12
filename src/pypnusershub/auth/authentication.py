import logging
from typing import Any, Union

from marshmallow import Schema, ValidationError, fields, validates_schema
from pypnusershub.db import models

log = logging.getLogger(__name__)


class ProviderConfigurationSchema(Schema):
    module = fields.Str(required=True)
    id_provider = fields.Str(required=True)
    group_mapping = fields.Dict(keys=fields.Str(), values=fields.Integer())
    logo = fields.String()
    label = fields.String()

    @validates_schema
    def check_if_module_exists(self, data, **kwargs):
        import importlib

        path_provider = data["module"]
        import_path, class_name = (
            ".".join(path_provider.split(".")[:-1]),
            path_provider.split(".")[-1],
        )
        try:
            importlib.import_module(import_path)
        except ModuleNotFoundError:
            raise ValidationError(f"Module {import_path} not found")
        try:
            getattr(importlib.import_module(import_path), class_name)
        except AttributeError:
            raise ValidationError(
                f"Class {class_name} not found in module {import_path}"
            )


class Authentication:
    """
    Abstract class for authentication implementations.
    """

    """
    Identifier of the instance of the authentication provider (str).
    Is override by provider config if provided
    """
    id_provider = None

    """
    Label of the authentication provider.
    Use in frontend
    """
    label = ""

    """
    Group mapping between source_group and destination_group. Must be in the following format:
    [{"grp_src":"admin","grp_dst":"Grp_admin"},...]
    """
    group_mapping = []

    """
    External login URL.
    Must be define if the authentication provider is external
    Not mandatory for OpenID Providers
    """
    login_url = ""

    """
    External logout URL.
    Must be define if the authentication provider is external
    Not mandatory for OpenID Providers
    """
    logout_url = ""

    """
    Logo of the authentication provider (str)
    URL or html of the logo image
    """
    logo = ""

    @property
    def is_external(self) -> bool:
        """
        Return whether the authentication is performed by the identity provider.

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
        Union[Response, models.User]
            The result of the authentication process, which can be either a Response object or a User object.
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

    def configure(self, configuration: Union[dict, Any] = {}) -> None:
        """
        Configure the authentication provider based on data in the configuration file.

        Parameters
        ----------
        configuration : Union[dict, Any], optional
            The configuration parameters.
            Default is an empty dictionary.

        """
        self.id_provider = configuration["id_provider"]
        for field in ["label", "logo", "login_url", "logout_url", "group_mapping"]:
            if field in configuration:
                setattr(self, field, configuration[field])
