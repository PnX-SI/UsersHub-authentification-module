from datetime import datetime
from typing import Any, Optional, Tuple, Union

import requests
from flask import Response, current_app, session, url_for
import sqlalchemy as sa
from marshmallow import EXCLUDE, ValidationError, fields
from pypnusershub.auth import Authentication, ProviderConfigurationSchema, oauth
from pypnusershub.auth.user_manager import UserManager
from pypnusershub.db import db, models
from pypnusershub.utils import get_current_app_id
from werkzeug.exceptions import Unauthorized
from enum import Enum


class UserColumns(str, Enum):
    """
    Enum listing the columns from the User model that can be modified.
    """

    ID_ROLE = "id_role"
    IDENTIFIANT = "identifiant"
    NOM_ROLE = "nom_role"
    PRENOM_ROLE = "prenom_role"
    EMAIL = "email"
    ACTIVE = "active"


class OpenIDProvider(Authentication):
    """
    OpenID provider authentication class.

    This class handle the authentication process with an OpenID provider.

    """

    logo = '<i class="fa fa-sign-in"></i>'
    is_external = True
    """
    Name of the fields in the OpenID token that contains the groups info
    """
    group_claim_name = "groups"
    identifier_field = "preferred_username"
    reconciliate_attr = "email"
    auto_validate_new_user = True

    def authenticate(self, *args, **kwargs) -> Union[Response, models.User]:
        redirect_uri = url_for(
            "auth.authorize", provider=self.id_provider, _external=True
        )
        oauth_provider = getattr(oauth, self.id_provider)
        return oauth_provider.authorize_redirect(redirect_uri)

    def authorize(self):
        oauth_provider = getattr(oauth, self.id_provider)
        token = oauth_provider.authorize_access_token()
        session["openid_token_resp"] = token
        user_info = token["userinfo"]
        new_user = {
            UserColumns.IDENTIFIANT: user_info.get(
                self.identifier_field,
                f"{user_info['given_name'].lower()}.{user_info['family_name'].lower()}",
            ),
            UserColumns.EMAIL: user_info["email"],
            UserColumns.PRENOM_ROLE: user_info["given_name"],
            UserColumns.NOM_ROLE: user_info["family_name"],
            UserColumns.ACTIVE: self.auto_validate_new_user,
        }
        source_groups = (
            user_info[self.group_claim_name]
            if self.group_claim_name in user_info
            else []
        )

        # Existing user
        existing_user = db.session.execute(
            sa.select(models.User).where(
                getattr(models.User, self.reconciliate_attr)
                == new_user[self.reconciliate_attr]
            )
        ).scalar_one_or_none()

        # Manual validation: existing users can still log in
        # Auto-validation: create/update user and allow login immediately
        if existing_user or self.auto_validate_new_user:
            user = self.insert_or_update_role(
                new_user,
                source_groups=source_groups,
                reconciliate_attr=self.reconciliate_attr,
                fields_to_update=self.fields_to_override,
            )
            db.session.commit()
            return user

        # Manual validation: new users create a temp request
        # - Avoid creating duplicate pending requests
        temp_user_exists = db.session.execute(
            sa.select(models.TempUser).where(
                getattr(models.TempUser, self.reconciliate_attr)
                == new_user[self.reconciliate_attr],
            )
        ).scalar_one_or_none()

        if temp_user_exists:
            raise self.PendingValidationAlreadyExistsError()

        # - create pending request
        temp_user = models.TempUser(
            token_role=UserManager.generate_token(),
            identifiant=new_user["identifiant"],
            nom_role=new_user["nom_role"],
            prenom_role=new_user["prenom_role"],
            email=new_user["email"],
            groupe=False,
            id_application=get_current_app_id(),
        )
        db.session.add(temp_user)
        db.session.commit()
        raise self.PendingValidationError()

    def revoke(self):
        if not "openid_token_resp" in session:
            raise Unauthorized()
        token_response = session["openid_token_resp"]
        oauth_provider = getattr(oauth, self.id_provider)
        metadata = oauth_provider.load_server_metadata()
        requests.post(
            metadata["revocation_endpoint"],
            data={
                "token": token_response["access_token"],
            },
        )
        session.pop("openid_token_resp")

    def configure(self, configuration: Union[dict, Any]) -> None:
        class OpenIDProviderConfiguration(ProviderConfigurationSchema):
            ISSUER = fields.String(required=True)
            CLIENT_ID = fields.String(required=True)
            CLIENT_SECRET = fields.String(required=True)
            group_claim_name = fields.String(load_default="groups")
            IDENTIFIER_FIELD = fields.String(
                load_default="preferred_username"
            )  # Claim d’identification du token OpenID/OIDC
            RECONCILIATE_ATTR = fields.String(load_default="email")
            AUTO_VALIDATE_NEW_USER = fields.Boolean(load_default=True)
            CODE_CHALLENGE_METHOD = fields.String(
                load_default="S256",
                validate=fields.validate.OneOf(["plain", "S256"]),
            )
            FIELDS_TO_OVERRIDE = fields.List(
                fields.Enum(UserColumns, by_value=True),
                load_default=[
                    UserColumns.NOM_ROLE,
                    UserColumns.PRENOM_ROLE,
                    UserColumns.EMAIL,
                ],
            )

        super().configure(configuration)
        try:
            configuration = OpenIDProviderConfiguration().load(
                configuration, unknown=EXCLUDE
            )
        except ValidationError as e:
            raise ValidationError(
                f"Error while loading OpenID provider configuration: {e}"
            )

        oauth.register(
            name=configuration["id_provider"],
            client_id=configuration["CLIENT_ID"],
            client_secret=configuration["CLIENT_SECRET"],
            server_metadata_url=f'{configuration["ISSUER"]}/.well-known/openid-configuration',
            client_kwargs={
                "scope": "openid email profile",
                "issuer": configuration["ISSUER"],
                "code_challenge_method": configuration["CODE_CHALLENGE_METHOD"],
            },
        )
        self.group_claim_name = configuration["group_claim_name"]
        self.identifier_field = configuration["IDENTIFIER_FIELD"]
        self.reconciliate_attr = configuration["RECONCILIATE_ATTR"]
        self.fields_to_override = configuration["FIELDS_TO_OVERRIDE"]
        self.auto_validate_new_user = configuration["AUTO_VALIDATE_NEW_USER"]


class OpenIDConnectProvider(OpenIDProvider):
    """
    OpenID Connect provider authentication class.

    This class handle the authentication process with an OpenID Connect provider.

    """

    def revoke(self):

        if not "openid_token_resp" in session:
            raise Unauthorized()
        token_response = session["openid_token_resp"]
        oauth_provider = getattr(oauth, self.id_provider)
        metadata = oauth_provider.load_server_metadata()
        requests.post(
            metadata["end_session_endpoint"],
            data={
                "client_id": oauth_provider.client_id,
                "client_secret": oauth_provider.client_secret,
                "refresh_token": token_response.get("refresh_token", ""),
            },
        )
        session.pop("openid_token_resp")
