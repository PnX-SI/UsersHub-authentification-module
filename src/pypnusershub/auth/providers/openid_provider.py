from typing import Any, Optional, Tuple, Union

import requests
from flask import Response, current_app, session, url_for
from marshmallow import EXCLUDE, ValidationError, fields
from pypnusershub.auth import Authentication, ProviderConfigurationSchema, oauth
from pypnusershub.db import db, models
from werkzeug.exceptions import Unauthorized


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
        source_groups = (
            user_info[self.group_claim_name]
            if self.group_claim_name in user_info
            else []
        )
        user = self.insert_or_update_role(new_user, source_groups=source_groups)
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

    def configure(self, configuration: Union[dict, Any]) -> None:

        super().configure(configuration)

        oauth.register(
            name=configuration["id_provider"],
            client_id=configuration["CLIENT_ID"],
            client_secret=configuration["CLIENT_SECRET"],
            server_metadata_url=f'{configuration["ISSUER"]}/.well-known/openid-configuration',
            client_kwargs={
                "scope": "openid email profile",
                "issuer": configuration["ISSUER"],
            },
        )

        class OpenIDProviderConfiguration(ProviderConfigurationSchema):
            ISSUER = fields.String(required=True)
            CLIENT_ID = fields.String(required=True)
            CLIENT_SECRET = fields.String(required=True)
            group_claim_name = fields.String(load_default="groups")

        try:
            configuration = OpenIDProviderConfiguration().load(
                configuration, unknown=EXCLUDE
            )
        except ValidationError as e:
            raise ValidationError(
                f"Error while loading OpenID provider configuration: {e}"
            )
        self.group_claim_name = configuration["group_claim_name"]


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
