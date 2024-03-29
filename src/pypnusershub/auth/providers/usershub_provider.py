import requests
from typing import Any, Optional, Tuple, Union

from marshmallow import Schema, fields

from flask import request, Response, url_for, current_app, redirect
from werkzeug.exceptions import Unauthorized
from sqlalchemy import select

from geonature.utils.env import db
from pypnusershub.auth import Authentication, ProviderConfigurationSchema
from pypnusershub.db.models import User
from pypnusershub.routes import insert_or_update_role


class ExternalUsersHubAuthProvider(Authentication):
    name = "EXTERNAL_USERSHUB_PROVIDER_CONFIG"
    logo = '<i class="fa fa-users"></i>'

    def authenticate(self):
        params = request.json
        login_response = requests.post(
            self.login_url,
            json={"login": params.get("login"), "password": params.get("password")},
        )
        if login_response.status_code != 200:
            raise Unauthorized(f"Connexion impossible à {self.label} ")
        user_resp = login_response.json()["user"]
        user = User(
            uuid_role=user_resp.get("uuid_role"),
            identifiant=user_resp["identifiant"],
            email=user_resp["email"],
            nom_role=user_resp["nom_role"],
            prenom_role=user_resp["prenom_role"],
        )
        return insert_or_update_role(user, provider_instance=self)

    @staticmethod
    def configuration_schema() -> Optional[Tuple[str, ProviderConfigurationSchema]]:
        class ExternalGNConfiguration(ProviderConfigurationSchema):
            login_url = fields.String(required=True)
            logout_url = fields.String(required=True)

        return ExternalGNConfiguration