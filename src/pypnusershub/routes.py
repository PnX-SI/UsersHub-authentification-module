# coding: utf8

from __future__ import absolute_import, division, print_function, unicode_literals

from pypnusershub.authentification import DefaultConfiguration

"""
routes relatives aux application, utilisateurs et à l'authentification
"""

import datetime
import json
import logging

import sqlalchemy as sa
from flask import (
    Blueprint,
    Response,
    current_app,
    g,
    jsonify,
    make_response,
    redirect,
    request,
)
from flask_login import current_user, login_required, login_user, logout_user
from markupsafe import escape
from pypnusershub.db import db, models
from pypnusershub.db.tools import encode_token
from pypnusershub.schemas import OrganismeSchema, UserSchema
from pypnusershub.utils import get_current_app_id
from sqlalchemy.orm import exc
from werkzeug.exceptions import BadRequest, Forbidden

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
        # set cookie autorenew
        app.config["PASS_METHOD"] = app.config.get("PASS_METHOD", "hash")

        app.config["REMEMBER_COOKIE_NAME"] = app.config.get(
            "REMEMBER_COOKIE_NAME", "token"
        )

        parent = super(ConfigurableBlueprint, self)
        parent.register(app, *args, **kwargs)

        @app.before_request
        def load_current_user():
            g.current_user = current_user


routes = ConfigurableBlueprint("auth", __name__)

# retrocompatibilité before 2.0
from pypnusershub.decorators import check_auth


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
    user_dict = UserSchema(exclude=["remarques"], only=["+max_level_profil"]).dump(
        g.current_user
    )

    token_exp = datetime.datetime.now(datetime.timezone.utc)
    token_exp += datetime.timedelta(seconds=current_app.config["COOKIE_EXPIRATION"])
    data = {
        "user": user_dict,
        "token": encode_token(g.current_user.as_dict()).decode(),
        "expires": token_exp.isoformat(),
    }

    return jsonify(data)


@routes.route("/external_provider_url")
def get_external_provider_url() -> str:
    """
    Retrieves the URL of the current authentication provider.

    This route is used to get the URL of the current authentication provider.
    It uses the `auth_manager` of the Flask app to get the current provider and
    then calls its `get_provider_url` method to get the URL.

    Returns
    -------
    str
        The URL of the current authentication provider.
    """
    return jsonify(current_app.auth_manager.get_current_provider().get_provider_url())


@routes.route("/external_provider_revoke_url")
def get_external_provider_revoke_url() -> str:
    """
    Retrieves the URL of the current authentication provider.

    This route is used to get the URL of the current authentication provider.
    It uses the `auth_manager` of the Flask app to get the current provider and
    then calls its `get_provider_url` method to get the URL.

    Returns
    -------
    str
        The URL of the current authentication provider.
    """
    return jsonify(
        current_app.auth_manager.get_current_provider().get_provider_revoke_url()
    )


@routes.route("/login", methods=["POST", "GET"])
def login():
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

    auth_result = current_app.auth_manager.get_current_provider().authenticate()
    if isinstance(auth_result, models.User):
        login_user(auth_result)
        user_dict = UserSchema(exclude=["remarques"], only=["+max_level_profil"]).dump(
            auth_result
        )
        token = encode_token(user_dict)
        token_exp = datetime.datetime.now(datetime.timezone.utc)
        token_exp += datetime.timedelta(seconds=current_app.config["COOKIE_EXPIRATION"])

        if current_app.config.get("CAS_AUTHENTIFICATION", False):
            return redirect(current_app.config["URL_APPLICATION"])
        return jsonify(
            {
                "user": user_dict,
                "expires": token_exp.isoformat(),
                "token": token.decode(),
            }
        )
    else:
        return auth_result


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
    token_exp += datetime.timedelta(seconds=current_app.config["COOKIE_EXPIRATION"])

    return jsonify(
        {"user": user_dict, "expires": token_exp.isoformat(), "token": token.decode()}
    )


@routes.route("/logout", methods=["GET", "POST"])
def logout():

    params = request.args
    if "redirect" in params:
        resp = redirect(params["redirect"], code=302)
    else:
        resp = make_response()

    logout_user()
    current_app.auth_manager.get_current_provider().revoke()

    return resp


def insert_or_update_organism(organism):
    """
    Insert a organism

    """
    organism_schema = OrganismeSchema()
    organism = organism_schema.load(organism)
    db.session.add(organism)
    return organism_schema.dump(organism)


def insert_or_update_role(data):
    """
    Insert or update a role (also add groups if provided)
    """
    user_schema = UserSchema(only=["groups"])
    user = user_schema.load(data)
    db.session.add(user)
    return user_schema.dump(user)
