# coding: utf8

from __future__ import unicode_literals, print_function, absolute_import, division


"""
routes relatives aux application, utilisateurs et à l'authentification
"""

import json
import logging

import datetime
from flask_login import login_user, logout_user, current_user
from flask import (
    Blueprint,
    request,
    Response,
    current_app,
    redirect,
    g,
    make_response,
    jsonify,
)
from markupsafe import escape

from sqlalchemy.orm import exc
import sqlalchemy as sa
from werkzeug.exceptions import BadRequest, Forbidden

from pypnusershub.utils import get_current_app_id
from pypnusershub.db import models, db
from pypnusershub.db.tools import (
    encode_token,
)
from pypnusershub.schemas import OrganismeSchema, UserSchema


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


@routes.route("/login", methods=["POST"])
def login():
    user_data = request.json
    try:
        login = user_data.get("login")
        password = user_data.get("password")
        id_app = user_data.get("id_application", get_current_app_id())
        if id_app is None or login is None or password is None:
            msg = json.dumps(
                "One of the following parameter is required ['id_application', 'login', 'password']"
            )
            return Response(msg, status=400)
        app = db.session.get(models.Application, id_app)
        if not app:
            raise BadRequest(f"No app for id {id_app}")
        user = db.session.execute(
            sa.select(models.User)
            .where(models.User.identifiant == login)
            .where(models.User.filter_by_app())
        ).scalar_one()
        user_dict = UserSchema(exclude=["remarques"], only=["+max_level_profil"]).dump(
            user
        )
    except exc.NoResultFound as e:
        msg = json.dumps(
            {
                "type": "login",
                "msg": (
                    'No user found with the username "{login}" for '
                    'the application with id "{id_app}"'
                ).format(login=escape(login), id_app=id_app),
            }
        )
        log.info(msg)
        status_code = current_app.config.get("BAD_LOGIN_STATUS_CODE", 490)
        return Response(msg, status=status_code)

    if not user.check_password(user_data["password"]):
        msg = json.dumps({"type": "password", "msg": "Mot de passe invalide"})
        log.info(msg)
        status_code = current_app.config.get("BAD_LOGIN_STATUS_CODE", 490)
        return Response(msg, status=status_code)
    login_user(user)
    # Génération d'un token
    token = encode_token(user_dict)
    token_exp = datetime.datetime.now(datetime.timezone.utc)
    token_exp += datetime.timedelta(seconds=current_app.config["COOKIE_EXPIRATION"])
    return jsonify(
        {"user": user_dict, "expires": token_exp.isoformat(), "token": token.decode()}
    )


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
