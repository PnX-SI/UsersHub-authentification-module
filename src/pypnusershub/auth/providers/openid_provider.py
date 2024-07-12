from typing import Any, Optional, Tuple, Union

import requests
from flask import Response, current_app, session, url_for
from marshmallow import EXCLUDE, ValidationError, fields
from pypnusershub.auth import Authentication, ProviderConfigurationSchema, oauth
from pypnusershub.db import db, models
from pypnusershub.routes import insert_or_update_role
from werkzeug.exceptions import Unauthorized


class OpenIDProvider(Authentication):
    """
    OpenID provider authentication class.

    This class handle the authentication process with an OpenID provider.

    """

    name = "OPENID_PROVIDER_CONFIG"
    logo = '<i class="fa fa-sign-in"></i>'
    is_external = False
    """
    Name of the fields in the OpenID token that contains the groups info
    """
    group_claim_name = "groups"

    def __init__(self):
        super().__init__()
        for provider in current_app.config["AUTHENTICATION"]["PROVIDERS"]:
            if not (
                provider["module"].endswith("OpenIDProvider")
                or provider["module"].endswith("OpenIDConnectProvider")
            ):
                continue
            oauth.register(
                name=provider["id_provider"],
                client_id=provider["CLIENT_ID"],
                client_secret=provider["CLIENT_SECRET"],
                server_metadata_url=f'{provider["ISSUER"]}/.well-known/openid-configuration',
                client_kwargs={
                    "scope": "openid email profile",
                    "issuer": provider["ISSUER"],
                },
            )

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
            "identifiant": f"{user_info['given_name'].lower()}.{user_info['family_name'].lower()}",
            "email": user_info["email"],
            "prenom_role": user_info["given_name"],
            "nom_role": user_info["family_name"],
            "active": True,
        }
        kwargs = (
            dict(group_keys=user_info[self.group_claim_name])
            if self.group_claim_name in user_info
            else {}
        )
        user = insert_or_update_role(new_user, provider_instance=self, **kwargs)
        db.session.commit()
        return user

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

    def configure(self, configuration: dict | Any) -> None:

        super().configure(configuration)

        class OpenIDProviderConfiguration(ProviderConfigurationSchema):
            ISSUER = fields.String(required=True)
            CLIENT_ID = fields.String(required=True)
            CLIENT_SECRET = fields.String(required=True)
            group_claim_name = fields.String(load_default="groups")

        try:
            OpenIDProviderConfiguration().load(configuration, unknown=EXCLUDE)
        except ValidationError as e:
            raise ValidationError(
                f"Error while loading OpenID provider configuration: {e}"
            )


class OpenIDConnectProvider(OpenIDProvider):
    """
    OpenID Connect provider authentication class.

    This class handle the authentication process with an OpenID Connect provider.

    """

    name = "OPENID_CONNECT_PROVIDER_CONFIG"

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
