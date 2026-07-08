# coding: utf8
"""
routes relatives aux application, utilisateurs et à l'authentification
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import logging
from typing import List
from urllib.parse import urlencode, urljoin

import requests
import sqlalchemy as sa
from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    redirect,
    request,
    session,
)
from flask_login import current_user, login_required, login_user, logout_user
from markupsafe import escape
from pypnusershub.auth import oauth
from pypnusershub.db import db, models
from pypnusershub.db.tools import encode_token
from pypnusershub.schemas import UserSchema
from pypnusershub.auth.authentication import Authentication
from pypnusershub.utils import get_current_app_id
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import Forbidden, Unauthorized

log = logging.getLogger(__name__)
# This module was originally designed as a submodule of designed
# to be a submodule for https://github.com/PnX-SI/TaxHub/
# The original behavior from the lib is to rely on the side effects of
# a file called "server.py" in TaxHub, specially a function "init_app()"
# that is globally called to initialised the current application object.
# To avoid coupling, we replaced most call to init_app() by flask.current_app,
# which does the same job in the context of a request.
# However, there are still 3 use cases not cover by this:
#  - TaxHub app initialization: be provide it by having a routes.py at the
#    root of this project where init_app() is imported and called. Because
#    it will be imported automatically by TaxHub, but only by TaxHub, it
#    should not cause problems.
#  - The cookie expiration is manage in a callback registered in init__app().
#    If we want this behavior to be preserved, we need to register the
#    callback as well, but we can't use current_app object because the
#    registration happens outside of the req/res cycle. Hence we create a
#    custom Blueprint object, which register method is called once the
#    root app object is created. We can then register the callback from here.
#    To avoid TaxHub to register this callback twice, the registration happens
#    only if we request it using a 'COOKIE_AUTORENEW' setting.
#  - The DB needs to be registered on the app. We use the same trick, but
#    but the param is called 'INIT_APP_WITH_DB' and default to True.
#  - the 'login' url must be configuratble. We provide this with the
#    'LOGIN_ROUTE' param, but we still default to '/login' and POST.


class ConfigurableBlueprint(Blueprint):
    def register(self, app, *args, **kwargs):
        app.config["PASS_METHOD"] = app.config.get("PASS_METHOD", "hash")

        app.config["REMEMBER_COOKIE_NAME"] = app.config.get(
            "REMEMBER_COOKIE_NAME", "token"
        )
        # retro-compat set COOKIE_EXPIRATION in REMEMBER_COOKIE_DURATION
        # (Flask Login parameter, default 1 year)
        app.config["REMEMBER_COOKIE_DURATION"] = app.config.get(
            "COOKIE_EXPIRATION", 31557600
        )
        parent = super(ConfigurableBlueprint, self)
        parent.register(app, *args, **kwargs)
        oauth.init_app(app)

        @app.before_request
        def load_current_user():
            g.current_user = current_user


routes = ConfigurableBlueprint("auth", __name__)

# retrocompatibilité before 2.0
from pypnusershub.decorators import check_auth


@routes.route("/providers", methods=["GET"])
def get_providers():
    from itertools import chain

    property_name = [
        "is_external",
        "logo",
        "label",
        "login_url",
        "logout_url",
        "is_secondary",
    ]
    return jsonify(
        [
            dict(
                chain.from_iterable(
                    d.items()
                    for d in (
                        {
                            _property: getattr(provider, _property)
                            for _property in property_name
                        },
                        {"id_provider": id_provider},
                    )
                )
            )
            for id_provider, provider in current_app.auth_manager.provider_authentication_cls.items()
        ]
    )


@routes.route("/get_current_user")
@login_required
def get_user_data():
    """
    Retrieves the data of the currently authenticated user.

    This route is protected and requires the user to be logged in. It retrieves the user data
    from the `g.current_user` object and serializes it using the `UserSchema` class. The serialized user data
    is then added to the response JSON along with a JWT token and the expiration time of the token.

    Returns
    -------
    dict
        A dictionary containing the user data, token, and expiration time.
    """
    user_dict_with_token = UserSchema(
        exclude=["remarques"], only=["+max_level_profil", "+providers", "organisme"]
    ).dump_with_token(g.current_user)

    return jsonify(user_dict_with_token)


@routes.route("/login/<provider>", methods=["POST", "GET"])
@routes.route(
    "/login", methods=["POST", "GET"], defaults={"provider": "local_provider"}
)
def login(provider):
    """
    Authenticates the user and returns their data and a JWT token.

    This route is called by the client to authenticate the user. It uses the
    `authentification_class` configured in the Flask app to authenticate the user.
    If the authentication is successful, it returns a JSON response containing
    the serialized user data, a JWT token, and the expiration time of the token.
    If the authentication fails, it returns the result of the authentication.

    Returns
    -------
    - If the authentication is successful, it returns a JSON response containing:
        - `user`: The serialized user data.
        - `expires`: The expiration time of the token.
        - `token`: The JWT token.
    - If the authentication fails, it returns the result of the authentication.
    """
    auth_provider = current_app.auth_manager.get_provider(provider)
    session["current_provider"] = provider
    auth_result = auth_provider.authenticate()
    if isinstance(auth_result, Response):
        return auth_result
    if isinstance(auth_result, models.User):
        login_user(auth_result, remember=True)
        user_dict_with_token = UserSchema(
            exclude=["remarques"], only=["+max_level_profil", "+providers", "organisme"]
        ).dump_with_token(auth_result)
        return jsonify(user_dict_with_token)


@routes.route("/public_login", methods=["POST"])
def public_login():
    if not current_app.config.get("PUBLIC_ACCESS_USERNAME", {}):
        raise Forbidden
    login = current_app.config.get("PUBLIC_ACCESS_USERNAME")

    user = db.session.execute(
        sa.select(models.User)
        .where(models.User.identifiant == login)
        .where(models.User.filter_by_app(code_app="GN"))
    ).scalar_one()

    login_user(user)

    return UserSchema(
        exclude=["remarques"], only=["+max_level_profil", "+providers", "organisme"]
    ).dump_with_token(user)


@routes.route("/logout", methods=["GET", "POST"])
def logout():
    if not "current_provider" in session:
        raise Unauthorized("No provider in session")
    auth_provider = current_app.auth_manager.get_provider(session["current_provider"])
    logout_user()
    resp = auth_provider.revoke()
    if isinstance(resp, Response):
        return resp

    params = request.args
    if "redirect" in params:
        resp = redirect(
            urljoin(current_app.config["URL_APPLICATION"], params["redirect"]),
            code=302,
        )
    else:
        resp = redirect(current_app.config["URL_APPLICATION"])

    return resp


@routes.route("/authorize/<provider>", methods=["GET", "POST"])
def authorize(provider="local_provider"):
    auth_provider = current_app.auth_manager.get_provider(provider)
    try:
        authorize_result = auth_provider.authorize()
    except (Unauthorized, Forbidden) as exc:
        log.exception("Authorization error for provider %s", provider)
        error_description = (
            getattr(exc, "error_code") or exc.description or "Unauthorized"
        )
        login_url = f"{current_app.config['URL_APPLICATION']}/#/login"
        query_params = {
            "login_error": error_description,
        }
        return redirect(f"{login_url}?{urlencode(query_params)}", code=302)

    if isinstance(authorize_result, models.User):
        login_user(authorize_result, remember=True)

    # if auth_provider.is_external:
    return redirect(current_app.config["URL_APPLICATION"])


@routes.route("/mobile/keycloak", methods=["POST"])
def mobile_keycloak():
    payload = request.get_json(silent=True) or {}
    provider_id = payload.get("provider_id", "keycloak")
    id_application = payload.get("id_application", get_current_app_id())
    provider_config = next(
        (
            p
            for p in current_app.config.get("AUTHENTICATION", {}).get("PROVIDERS", [])
            if p.get("id_provider") == provider_id
        ),
        {},
    )

    for field in ("code", "code_verifier", "redirect_uri"):
        if not payload.get(field):
            return (
                jsonify(
                    {
                        "type": "invalid_request",
                        "message": f"Missing '{field}'",
                    }
                ),
                400,
            )

    if id_application is None:
        return (
            jsonify(
                {
                    "type": "invalid_request",
                    "message": "Missing 'id_application'",
                }
            ),
            400,
        )

    allowed_redirect_uris = (
        provider_config.get("MOBILE_REDIRECT_URIS")
        or provider_config.get("VALID_REDIRECT_URIS")
        or []
    )
    if allowed_redirect_uris and payload["redirect_uri"] not in allowed_redirect_uris:
        return (
            jsonify(
                {
                    "type": "invalid_request",
                    "message": "Invalid 'redirect_uri'",
                }
            ),
            400,
        )

    try:
        auth_provider = current_app.auth_manager.get_provider(provider_id)
    except KeyError:
        return (
            jsonify(
                {
                    "type": "invalid_request",
                    "message": f"Unknown provider '{provider_id}'",
                }
            ),
            400,
        )

    oauth_provider = getattr(oauth, provider_id, None)
    if oauth_provider is None:
        return (
            jsonify(
                {
                    "type": "invalid_request",
                    "message": f"OAuth provider '{provider_id}' is not configured",
                }
            ),
            400,
        )

    metadata = oauth_provider.load_server_metadata()
    token_endpoint = metadata.get("token_endpoint")
    if not token_endpoint:
        return (
            jsonify(
                {
                    "type": "server_error",
                    "message": "Missing token endpoint for provider configuration",
                }
            ),
            500,
        )

    token_request = {
        "grant_type": "authorization_code",
        "code": payload["code"],
        "code_verifier": payload["code_verifier"],
        "redirect_uri": payload["redirect_uri"],
        "client_id": oauth_provider.client_id,
    }
    if oauth_provider.client_secret:
        token_request["client_secret"] = oauth_provider.client_secret

    token_response = requests.post(token_endpoint, data=token_request, timeout=10)
    if not token_response.ok:
        return (
            jsonify(
                {
                    "type": "invalid_grant",
                    "message": "Authorization code is invalid or expired",
                }
            ),
            401,
        )

    token_data = token_response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return (
            jsonify(
                {
                    "type": "invalid_grant",
                    "message": "Authorization code is invalid or expired",
                }
            ),
            401,
        )

    userinfo = {}
    userinfo_endpoint = metadata.get("userinfo_endpoint")
    if userinfo_endpoint:
        userinfo_response = requests.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if not userinfo_response.ok:
            return (
                jsonify(
                    {
                        "type": "invalid_grant",
                        "message": "Authorization code is invalid or expired",
                    }
                ),
                401,
            )
        userinfo = userinfo_response.json()

    if not userinfo:
        return (
            jsonify(
                {
                    "type": "invalid_grant",
                    "message": "Unable to recover user claims",
                }
            ),
            401,
        )

    source_groups = []
    group_claim_name = getattr(auth_provider, "group_claim_name", "groups")
    if group_claim_name in userinfo:
        source_groups = userinfo[group_claim_name] or []

    try:
        organism = None
        if hasattr(auth_provider, "_resolve_organism"):
            organism = auth_provider._resolve_organism(userinfo, source_groups)

        identifier_field = getattr(auth_provider, "identifier_field", "preferred_username")
        identifier = userinfo.get(identifier_field) or userinfo.get("preferred_username")
        if not identifier:
            return (
                jsonify(
                    {
                        "type": "invalid_grant",
                        "message": f"Missing '{identifier_field}' in user claims",
                    }
                ),
                401,
            )

        new_user = {
            "identifiant": identifier,
            "email": userinfo.get("email"),
            "prenom_role": userinfo.get("given_name") or "",
            "nom_role": userinfo.get("family_name") or "",
            "active": True,
        }

        user_uuid_claim = getattr(auth_provider, "user_uuid_claim", "sub")
        if userinfo.get(user_uuid_claim):
            new_user["uuid_role"] = userinfo[user_uuid_claim]
        if organism:
            new_user["id_organisme"] = organism.id_organisme

        user = auth_provider.insert_or_update_role(
            new_user,
            source_groups=source_groups,
            reconciliate_attr="identifiant",
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return (
            jsonify(
                {
                    "type": "reconciliation_error",
                    "message": "Unable to reconcile user organism",
                }
            ),
            409,
        )

    app_user = db.session.execute(
        sa.select(models.AppUser)
        .where(models.AppUser.id_role == user.id_role)
        .where(models.AppUser.id_application == id_application)
    ).scalar_one_or_none()
    if app_user is None:
        return (
            jsonify(
                {
                    "type": "forbidden",
                    "message": "User is not allowed for this application",
                }
            ),
            403,
        )

    user_payload = UserSchema(
        exclude=["remarques"], only=["+max_level_profil", "+providers"]
    ).dump_with_token(user)
    user_payload["user"]["id_application"] = int(id_application)
    user_payload["token"] = encode_token(user_payload["user"]).decode()
    return jsonify(user_payload)
