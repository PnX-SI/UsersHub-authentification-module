# coding: utf8
"""
routes relatives aux application, utilisateurs et à l'authentification
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import logging
from typing import List

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
from pypnusershub.schemas import OrganismeSchema, UserSchema
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
        "is_uh",
        "logo",
        "label",
        "login_url",
        "logout_url",
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
            if not provider.id_provider == "local_provider"
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
    user_dict = UserSchema(
        exclude=["remarques"], only=["+max_level_profil", "+providers"]
    ).dump(g.current_user)

    token_exp = datetime.datetime.now(datetime.timezone.utc)
    token_exp += datetime.timedelta(seconds=current_app.config["COOKIE_EXPIRATION"])
    data = {
        "user": user_dict,
        "token": encode_token(g.current_user.as_dict()).decode(),
        "expires": token_exp.isoformat(),
    }

    return jsonify(data)


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
        user_dict = UserSchema(
            exclude=["remarques"], only=["+max_level_profil", "+providers"]
        ).dump(auth_result)
        token = encode_token(user_dict)
        token_exp = datetime.datetime.now(datetime.timezone.utc)
        token_exp += datetime.timedelta(seconds=current_app.config["COOKIE_EXPIRATION"])

        return jsonify(
            {
                "user": user_dict,
                "expires": token_exp.isoformat(),
                "token": token.decode(),
            }
        )
    return redirect(current_app.config["URL_APPLICATION"])


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

    user_dict = user.as_dict()
    login_user(user)
    # Génération d'un token
    token = encode_token(user_dict)
    token_exp = datetime.datetime.now(datetime.timezone.utc)
    token_exp += datetime.timedelta(
        seconds=current_app.config["REMEMBER_COOKIE_DURATION"]
    )

    return jsonify(
        {"user": user_dict, "expires": token_exp.isoformat(), "token": token.decode()}
    )


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
        resp = redirect(params["redirect"], code=302)
    else:
        resp = redirect(current_app.config["URL_APPLICATION"])

    return resp


@routes.route("/authorize/<provider>", methods=["GET", "POST"])
def authorize(provider="local_provider"):
    auth_provider = current_app.auth_manager.get_provider(provider)
    authorize_result = auth_provider.authorize()
    if isinstance(authorize_result, models.User):
        login_user(authorize_result, remember=True)

    # if auth_provider.is_external:
    return redirect(current_app.config["URL_APPLICATION"])


def insert_or_update_organism(organism):
    """
    Insert a organism

    """
    organism_schema = OrganismeSchema()
    organism = organism_schema.load(organism)
    db.session.add(organism)
    return organism_schema.dump(organism)


def insert_or_update_role(
    user: models.User,
    provider_instance: models.Provider,
    reconciliate_attr="email",
    group_keys: List[int] = [],
) -> models.User:
    """
    Insert or update a role (also add groups if provided)

    Parameters
    ----------
    user: models.User
        User to insert or update
    provider_instance: models.Provider
        Provider instance used to create/log the user
    reconciliate_attr: str, default="email"
        Attribute used to reconciliate existing users
    group_keys: List[int], default=[]
        List of group keys to compare with existing groups defined in the group_mapping properties of the provider

    Returns
    -------
    models.User
        The updated or created user

    Raises
    ------
    Exception
        If no group mapping indicated for the provider and DEFAULT_RECONCILIATION_GROUP_ID
        is not set
    KeyError
        If Group {group_name} was not found in the mapping
    """
    assert hasattr(user, reconciliate_attr)

    user_exists = db.session.execute(
        sa.select(models.User).where(
            getattr(models.User, reconciliate_attr) == getattr(user, reconciliate_attr),
        )
    ).scalar_one_or_none()
    provider = db.session.execute(
        sa.select(models.Provider).where(
            models.Provider.name == provider_instance.id_provider
        )
    ).scalar_one()
    if user_exists:

        if not provider in user_exists.providers:
            user_exists.providers.append(provider)
            db.session.commit()
        return user_exists
    else:
        group_id = ""
        # No group mapping indicated
        if not (provider_instance.group_mapping and group_keys):

            if "DEFAULT_RECONCILIATION_GROUP_ID" in current_app.config.get(
                "AUTHENTICATION", {}
            ):

                group_id = current_app.config["AUTHENTICATION"][
                    "DEFAULT_RECONCILIATION_GROUP_ID"
                ]
                group = db.session.get(models.User, group_id)
                if group:
                    user.groups.append(group)
        # Group Mapping indicated
        else:
            for key in group_keys:
                if not key in provider_instance.group_mapping:
                    raise KeyError("Group {group_name} was not found in the mapping !")
                group_id = provider_instance.group_mapping[key]

                group = db.session.get(models.User, group_id)

                if group:
                    user.groups.append(group)

        user.providers.append(provider)
        db.session.add(user)
        db.session.commit()
        return user
