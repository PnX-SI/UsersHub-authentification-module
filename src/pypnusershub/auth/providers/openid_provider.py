import logging
from datetime import datetime
from typing import Any, Optional, Tuple, Union

import requests
from authlib.integrations.base_client import OAuthError
from flask import Response, current_app, request, session, url_for, redirect
import sqlalchemy as sa
from marshmallow import EXCLUDE, ValidationError, fields
from pypnusershub.auth import Authentication, ProviderConfigurationSchema, oauth
from pypnusershub.auth.user_manager import UserManager
from pypnusershub.db import db, models
from pypnusershub.utils import get_current_app_id
from werkzeug.exceptions import Unauthorized
from enum import Enum

log = logging.getLogger(__name__)


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


class OAuth2Provider(Authentication):
    """
    OAuth2 provider authentication class.

    This class handles the authentication process with a plain OAuth 2.0
    provider (token issuance/revocation), with no identity/session layer.
    Use OpenIDConnectProvider for providers exposing an OpenID Connect layer
    (id_token, SSO session logout, ...) on top of OAuth2.

    Formerly named ``OpenIDProvider``; kept available under that name below
    for backward compatibility with existing configurations.
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
        credentials = request.json if request.is_json else None
        if (
            self.ropc_flow
            and credentials
            and "login" in credentials
            and "password" in credentials
        ):
            return self._authenticate_password_grant(credentials)

        redirect_uri = url_for(
            "auth.authorize", provider=self.id_provider, _external=True
        )
        oauth_provider = getattr(oauth, self.id_provider)
        authorize_kwargs = {}
        if request.args.get("prompt"):
            authorize_kwargs["prompt"] = request.args["prompt"]
        return oauth_provider.authorize_redirect(redirect_uri, **authorize_kwargs)

    def _authenticate_password_grant(self, credentials: dict) -> models.User:
        """
        Resource Owner Password Credentials grant: lets a
        programmatic/API client authenticate directly with a login/password
        against the identity provider, without going through the
        browser-based authorization code flow.
        """
        oauth_provider = getattr(oauth, self.id_provider)
        try:
            token = oauth_provider.fetch_access_token(
                grant_type="password",
                username=credentials["login"],
                password=credentials["password"],
            )
        except OAuthError as e:
            log.warning(
                "Password grant failed for provider %s: %s", self.id_provider, e
            )
            raise self.IncorrectLoginError()
        return self._reconcile_user(token)

    def authorize(self):
        oauth_provider = getattr(oauth, self.id_provider)
        token = oauth_provider.authorize_access_token()
        return self._reconcile_user(token)

    def _fetch_userinfo(self, token: dict) -> dict:
        """
        Plain OAuth2 has no identity layer: the token is opaque, so the
        only way to get the user's identity is to call the provider's
        userinfo endpoint with the access token.
        """
        oauth_provider = getattr(oauth, self.id_provider)
        return oauth_provider.userinfo(token=token)

    def _reconcile_user(self, token: dict) -> models.User:
        session["openid_token_resp"] = {
            key: token[key]
            for key in ("access_token", "id_token", "refresh_token")
            if key in token
        }
        user_info = self._fetch_userinfo(token)
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
        token_response = session.pop("openid_token_resp")
        oauth_provider = getattr(oauth, self.id_provider)
        metadata = oauth_provider.load_server_metadata()
        requests.post(
            metadata["revocation_endpoint"],
            data={
                "token": token_response["access_token"],
                "client_id": oauth_provider.client_id,
                "client_secret": oauth_provider.client_secret,
            },
        )
        return self._redirect_to_login_prompt()

    def _redirect_to_login_prompt(self):
        return redirect(
            url_for("auth.login", prompt="login", provider=self.id_provider)
        )

    def configure(self, configuration: Union[dict, Any]) -> None:
        class OAuth2ProviderConfiguration(ProviderConfigurationSchema):
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
            ROPC_FLOW = fields.Boolean(load_default=False)

        super().configure(configuration)
        try:
            configuration = OAuth2ProviderConfiguration().load(
                configuration, unknown=EXCLUDE
            )
        except ValidationError as e:
            raise ValidationError(
                f"Error while loading OAuth2 provider configuration: {e}"
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
        self.ropc_flow = configuration["ROPC_FLOW"]


class OpenIDConnectProvider(OAuth2Provider):
    """
    OpenID Connect provider authentication class.

    This class handle the authentication process with an OpenID Connect provider.

    """

    sso_logout = True

    def _fetch_userinfo(self, token: dict) -> dict:
        # Unlike plain OAuth2, OIDC already carries the user's identity in
        # the id_token: Authlib decodes and exposes it as token["userinfo"],
        # so no extra call to the userinfo endpoint is needed.
        return token["userinfo"]

    def configure(self, configuration: Union[dict, Any]) -> None:
        class OpenIDConnectProviderConfiguration(ProviderConfigurationSchema):
            SSO_LOGOUT = fields.Boolean(load_default=True)

        super().configure(configuration)
        try:
            oidc_configuration = OpenIDConnectProviderConfiguration().load(
                configuration, unknown=EXCLUDE
            )
        except ValidationError as e:
            raise ValidationError(
                f"Error while loading OpenID Connect provider configuration: {e}"
            )
        self.sso_logout = oidc_configuration["SSO_LOGOUT"]

    def revoke(self):
        if not "openid_token_resp" in session:
            raise Unauthorized()
        token_response = session.pop("openid_token_resp")

        if self.sso_logout:
            # RP-Initiated Logout (Single Logout): terminates the SSO session
            # at the identity provider, not just for this app.
            oauth_provider = getattr(oauth, self.id_provider)
            return oauth_provider.logout_redirect(
                id_token_hint=token_response.get("id_token"),
                client_id=oauth_provider.client_id,
            )

        return self._redirect_to_login_prompt()


# Legacy alias: this class used to be named OpenIDProvider, despite only
# implementing plain OAuth2 (no identity/session layer). Kept for backward
# compatibility with existing "module" paths in AUTHENTICATION.PROVIDERS config.
OpenIDProvider = OAuth2Provider
