import logging
from typing import Any, Optional, Tuple, Union

import requests
import xmltodict
from flask import Response, current_app, redirect, render_template, request, url_for
from marshmallow import EXCLUDE, ValidationError, fields
from marshmallow import fields
from pypnusershub.auth import Authentication, ProviderConfigurationSchema
from pypnusershub.db import db, models
from pypnusershub.routes import insert_or_update_organism, insert_or_update_role
from sqlalchemy import select
from werkzeug.exceptions import InternalServerError

log = logging.getLogger()


class AuthenficationCASINPN(Authentication):
    name = "CAS_INPN_PROVIDER"
    label = "INPN"
    is_external = True
    logo = "<i class='fa fa-paw' aria-hidden='true'></i>"

    @property
    def logout_url(self):
        return f"{self.URL_LOGOUT}?service={current_app.config['URL_APPLICATION']}"

    def authenticate(self, *args, **kwargs) -> Union[Response, models.User]:
        redirect_uri = url_for(
            "auth.authorize", provider=self.id_provider, _external=True
        )

        return redirect(f"{self.URL_LOGIN}?service={redirect_uri}")

    def authorize(self):
        user = None
        redirect_uri = url_for(
            "auth.authorize", provider=self.id_provider, _external=True
        )

        if not "ticket" in request.args:
            return redirect(f"{self.URL_LOGIN}?service={redirect_uri}")

        ticket = request.args["ticket"]
        base_url = (
            f"{current_app.config['API_ENDPOINT']}/auth/authorize/{self.id_provider}"
        )
        url_validate = f"{self.URL_VALIDATION}?ticket={ticket}&service={base_url}"

        response = requests.get(url_validate)
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
        response = requests.get(
            ws_user_url,
            (
                self.WS_ID,
                self.WS_PASSWORD,
            ),
        )

        if response.status_code != 200:
            raise InternalServerError("Error with the inpn authentification service")

        info_user = response.json()
        user = self.insert_user_and_org(info_user)
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

    def insert_user_and_org(self, info_user):
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
            raise InternalServerError(
                "CAS ERROR: no ID or LOGIN provided",
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
        user = insert_or_update_role(user_info, provider_instance=self)
        if not user.groups:
            if not self.USERS_CAN_SEE_ORGANISM_DATA or organism_id is None:
                # group socle 1
                group_id = self.ID_USER_SOCLE_1
            else:
                # group socle 2
                group_id = self.ID_USER_SOCLE_2
            group = db.session.get(models.User, group_id)
            user.groups.append(group)
        return user

    def configure(self, configuration: Union[dict, Any]):
        super().configure(configuration)

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
            USERS_CAN_SEE_ORGANISM_DATA = fields.Boolean(load_default=False)
            ID_USER_SOCLE_1 = fields.Integer(load_default=7)
            ID_USER_SOCLE_2 = fields.Integer(load_default=6)

        try:
            configuration = CASINPNConfiguration().load(configuration, unknown=EXCLUDE)
        except ValidationError as e:
            raise ValidationError(f"Error in CAS INPN configuration {str(e)}")
        for key in configuration:
            setattr(self, key, configuration[key])
