from typing import Any, Optional, Tuple, Union

from authlib.integrations.flask_client import OAuth
from flask import (
    Response,
    current_app,
    url_for,
)
from marshmallow import Schema, fields

from pypnusershub.auth import Authentication, ProviderConfigurationSchema, oauth
from pypnusershub.db import models, db
from pypnusershub.db.models import User
from pypnusershub.routes import insert_or_update_role
import sqlalchemy as sa


# TODO : à enlever : fonctionne avec OPENID_PROVIDER

CONF_URL = "https://accounts.google.com/.well-known/openid-configuration"
oauth.register(
    name="google",
    server_metadata_url=CONF_URL,
    client_kwargs={"scope": "openid email profile"},
)


class GoogleAuthProvider(Authentication):
    name = "GOOGLE_PROVIDER_CONFIG"
    id_provider = "google"
    label = "Google"
    is_uh = False
    login_url = ""
    logout_url = ""
    logo = '<i class="fa fa-google"></i>'

    def authenticate(self, *args, **kwargs) -> Union[Response, models.User]:
        redirect_uri = url_for(
            "auth.authorize", provider=self.id_provider, _external=True
        )
        return oauth.google.authorize_redirect(redirect_uri)

    def authorize(self):
        token = oauth.google.authorize_access_token()
        user_info = token["userinfo"]
        new_user = {
            "identifiant": f"{user_info['given_name'].lower()}{user_info['family_name'].lower()}",
            "email": user_info["email"],
            "prenom_role": user_info["given_name"],
            "nom_role": user_info["family_name"],
            "active": True,
        }
        return insert_or_update_role(User(**new_user), provider_name=self.id_provider)

        return user

    @staticmethod
    def configuration_schema() -> Optional[Tuple[str, ProviderConfigurationSchema]]:
        class GoogleProviderConfiguration(ProviderConfigurationSchema):
            GOOGLE_CLIENT_ID = fields.String(load_default="")
            GOOGLE_CLIENT_SECRET = fields.String(load_default="")

        return GoogleProviderConfiguration

    def configure(self, configuration: Union[dict, Any]):
        super().configure(configuration)
        current_app.config["GOOGLE_CLIENT_ID"] = configuration["GOOGLE_CLIENT_ID"]
        current_app.config["GOOGLE_CLIENT_SECRET"] = configuration[
            "GOOGLE_CLIENT_SECRET"
        ]


# Accueil : https://ginco2-preprod.mnhn.fr/ (URL publique) + http://ginco2-preprod.patnat.mnhn.fr/ (URL privée)
