import logging
from typing import Any, Optional, Tuple, Union

import xmltodict
from flask import (
    Response,
    current_app,
    make_response,
    redirect,
    render_template,
    request,
)
from marshmallow import fields
from geonature.utils import utilsrequests
from geonature.utils.errors import GeonatureApiError
from pypnusershub.auth import Authentication, ProviderConfigurationSchema
from pypnusershub.db import db, models
from pypnusershub.routes import insert_or_update_organism, insert_or_update_role
from sqlalchemy import select

log = logging.getLogger()


class CasAuthentificationError(GeonatureApiError):
    pass


AUTHENTIFICATION_CONFIG = {
    "PROVIDER_NAME": "inpn",
    "EXTERNAL_PROVIDER": True,
}

CAS_AUTHENTIFICATION = True
CAS_PUBLIC = dict(
    URL_LOGIN="https://inpn.mnhn.fr/auth/login",
    URL_LOGOUT="https://inpn.mnhn.fr/auth/logout",
    URL_VALIDATION="https://inpn.mnhn.fr/auth/serviceValidate",
)

CAS_USER_WS = dict(
    URL="https://inpn.mnhn.fr/authentication/information",
    BASE_URL="https://inpn.mnhn.fr/authentication/",
    ID="change_value",
    PASSWORD="change_value",
)
USERS_CAN_SEE_ORGANISM_DATA = False

ID_USER_SOCLE_1 = 1
ID_USER_SOCLE_2 = 2


class AuthenficationCASINPN(Authentication):
    name = "CAS_INPN_PROVIDER"
    label = "INPN"
    is_uh = False
    logo = "<i class='fa fa-paw' aria-hidden='true'></i>"

    @property
    def login_url(self):
        gn_api = f"{current_app.config['API_ENDPOINT']}/auth/authorize/cas_inpn"
        return f"{self.URL_LOGIN}?service={gn_api}"

    @property
    def logout_url(self):
        return f"{self.URL_LOGOUT}?service={current_app.config['URL_APPLICATION']}"

    def authenticate(self, *args, **kwargs) -> Union[Response, models.User]:
        return redirect(self.login_url)

    def authorize(self):
        user = None

        if not "ticket" in request.args:
            return redirect(self.login_url)

        ticket = request.args["ticket"]
        base_url = (
            f"{current_app.config['API_ENDPOINT']}/auth/authorize/{self.id_provider}"
        )
        url_validate = f"{self.URL_VALIDATION}?ticket={ticket}&service={base_url}"

        response = utilsrequests.get(url_validate)
        xml_dict = xmltodict.parse(response.content)

        if "cas:authenticationSuccess" in xml_dict["cas:serviceResponse"]:
            user = xml_dict["cas:serviceResponse"]["cas:authenticationSuccess"][
                "cas:user"
            ]

        if not user:
            log.info("Erreur d'authentification lié au CAS, voir log du CAS")
            log.error("Erreur d'authentification lié au CAS, voir log du CAS")
            return render_template(
                "cas_login_error.html",
                cas_logout=self.URL_LOGOUT,
                url_geonature=current_app.config["URL_APPLICATION"],
            )

        ws_user_url = f"{self.URL_INFO}/{user}/?verify=false"
        response = utilsrequests.get(
            ws_user_url,
            (
                self.WS_ID,
                self.WS_PASSWORD,
            ),
        )

        if response.status_code != 200:
            raise CasAuthentificationError(
                "Error with the inpn authentification service", status_code=500
            )

        info_user = response.json()
        user = self.insert_user_and_org(info_user, self.id_provider)
        db.session.commit()
        organism_id = info_user["codeOrganisme"]
        if not organism_id:
            organism_id = (
                db.session.execute(
                    select(models.Organisme).filter_by(nom_organisme="Autre"),
                )
                .scalar_one()
                .id_organisme,
            )
        # user.id_organisme = organism_id
        return user

    def revoke(self) -> Any:
        return redirect(self.logout_url)

    def insert_user_and_org(self, info_user, id_provider):
        organism_id = info_user["codeOrganisme"]
        if info_user["libelleLongOrganisme"] is not None:
            organism_name = info_user["libelleLongOrganisme"]
        else:
            organism_name = "Autre"

        user_login = info_user["login"]
        user_id = info_user["id"]
        try:
            assert user_id is not None and user_login is not None
        except AssertionError:
            log.error("'CAS ERROR: no ID or LOGIN provided'")
            raise CasAuthentificationError(
                "CAS ERROR: no ID or LOGIN provided", status_code=500
            )
        # Reconciliation avec base GeoNature
        if organism_id:
            organism = {"id_organisme": organism_id, "nom_organisme": organism_name}
            insert_or_update_organism(organism)
        user_info = {
            "id_role": user_id,
            "identifiant": user_login,
            "nom_role": info_user["nom"],
            "prenom_role": info_user["prenom"],
            "id_organisme": organism_id,
            "email": info_user["email"],
            "active": True,
        }
        user = insert_or_update_role(
            models.User(**user_info), provider_name=self.id_provider
        )
        if not user.groups:
            if not USERS_CAN_SEE_ORGANISM_DATA or organism_id is None:
                # group socle 1
                group_id = ID_USER_SOCLE_1
            else:
                # group socle 2
                group_id = ID_USER_SOCLE_2
            group = db.session.get(models.User, group_id)
            user.groups.append(group)
        return user

    @staticmethod
    def configuration_schema() -> Optional[Tuple[str, ProviderConfigurationSchema]]:
        class CASINPNConfiguration(ProviderConfigurationSchema):
            URL_LOGIN = fields.String(load_default="https://inpn.mnhn.fr/auth/login")
            URL_LOGOUT = fields.String(load_default="https://inpn.mnhn.fr/auth/logout")
            URL_VALIDATION = fields.String(
                load_default="https://inpn.mnhn.fr/auth/serviceValidate"
            )
            URL_AUTHORIZE = fields.String(
                load_default="https://inpn.mnhn.fr/authentication/"
            )
            URL_INFO = fields.String(
                load_default="https://inpn.mnhn.fr/authentication/information",
            )
            WS_ID = fields.String(required=True)
            WS_PASSWORD = fields.String(required=True)

        return CASINPNConfiguration

    def configure(self, configuration: Union[dict, Any]):
        super().configure(configuration)
        print(configuration)
        for key in configuration:
            setattr(self, key, configuration[key])
