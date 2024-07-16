from typing import Any, Optional, Tuple, Union

import requests
from flask import request
from marshmallow import EXCLUDE, ValidationError, fields
from pypnusershub.auth import Authentication, ProviderConfigurationSchema
from pypnusershub.db.models import User
from werkzeug.exceptions import Unauthorized


class ExternalUsersHubAuthProvider(Authentication):
    """
    Authentication provider for Flask application using UsersHub-authentification-module.
    """

    name = "EXTERNAL_USERSHUB_PROVIDER_CONFIG"
    logo = '<i class="fa fa-users"></i>'
    is_external = False

    def authenticate(self):
        params = request.json
        login_response = requests.post(
            self.login_url,
            json={"login": params.get("login"), "password": params.get("password")},
        )
        if login_response.status_code != 200:
            raise Unauthorized(f"Connexion impossible à {self.label} ")
        user_resp = login_response.json()["user"]
        user_dict = dict(
            identifiant=user_resp["identifiant"],
            email=user_resp["email"],
            nom_role=user_resp["nom_role"],
            prenom_role=user_resp["prenom_role"],
        )
        if "uuid_role" in user_dict:
            user_dict["uuid_role"] = user_resp.get("uuid_role")
        return self.insert_or_update_role(user_dict)

    def configure(self, configuration: Union[dict, Any]) -> None:

        class ExternalGNConfiguration(ProviderConfigurationSchema):
            login_url = fields.String(required=True)
            logout_url = fields.String(required=True)

        try:
            configuration = ExternalGNConfiguration().load(
                configuration, unknown=EXCLUDE
            )
        except ValidationError as e:
            raise ValidationError(
                f"Error while loading OpenID provider configuration: {e}"
            )
        super().configure(configuration)
