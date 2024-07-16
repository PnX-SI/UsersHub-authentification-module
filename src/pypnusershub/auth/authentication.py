import logging
from typing import Any, Union, List

import sqlalchemy as sa

from flask import current_app
from marshmallow import Schema, ValidationError, fields, validates_schema
from pypnusershub.db import models
from pypnusershub.db import db, models


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
    {"grp_src":"grp_dst",...}
    """
    group_mapping = {}

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

    def insert_or_update_role(
        self,
        user_dict: dict,
        reconciliate_attr="email",
        source_groups: List[int] = [],
    ) -> models.User:
        """
        Insert or update a role (also add groups if provided)

        Parameters
        ----------
        user: models.User
            User to insert or update
        reconciliate_attr: str, default="email"
            Attribute used to reconciliate existing users
        source_groups: List[str], default=[]
            List of group names to compare with existing groups defined in the group_mapping properties of the provider

        Returns
        -------
        models.User
            The updated or created user

        Raises
        ------
        Exception
            If no group mapping indicated for the provider and DEFAULT_RECONCILIATION_GROUP_ID
            is not set
        KeyError
            If Group {group_name} was not found in the mapping
        """

        assert reconciliate_attr in user_dict

        user_exists = db.session.execute(
            sa.select(models.User).where(
                getattr(models.User, reconciliate_attr) == user_dict[reconciliate_attr],
            )
        ).scalar_one_or_none()

        provider = db.session.execute(
            sa.select(models.Provider).where(models.Provider.name == self.id_provider)
        ).scalar_one_or_none()
        if not provider:
            provider = models.Provider(name=self.id_provider, url=self.login_url)
            db.session.add()
            db.session.commit()

        if user_exists:
            if not provider in user_exists.providers:
                user_exists.providers.append(provider)

            for attr_key, attr_value in user_dict.items():
                setattr(user_exists, attr_key, attr_value)
            db.session.commit()
            return user_exists
        else:
            user_ = models.User(**user_dict)
            group_id = ""
            # No group mapping indicated
            if not (self.group_mapping and source_groups):

                if "DEFAULT_RECONCILIATION_GROUP_ID" in current_app.config.get(
                    "AUTHENTICATION", {}
                ):

                    group_id = current_app.config["AUTHENTICATION"][
                        "DEFAULT_RECONCILIATION_GROUP_ID"
                    ]
                    group = db.session.get(models.User, group_id)
                    if group:
                        user_.groups.append(group)
            # Group Mapping indicated
            else:
                for group_source_name in source_groups:
                    group_id = self.group_mapping.get(group_source_name, None)
                    if group_id:
                        group = db.session.get(models.User, group_id)
                        if group and not group in user_.groups:
                            user_.groups.append(group)

            user_.providers.append(provider)
            db.session.add(user_)
            db.session.commit()
            return user_
