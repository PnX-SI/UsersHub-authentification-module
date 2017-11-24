# coding: utf8

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)
"""
    DB tools not related to any model in particular.
"""

from flask import current_app

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import create_engine

from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
                          SignatureExpired, BadSignature)

from pypnusershub.db import models
from pypnusershub.utils import text_resource_stream


class AccessRightsError(Exception):
    pass


class InsufficientRightsError(AccessRightsError):
    pass


class AccessRightsExpiredError(AccessRightsError):
    pass


class UnreadableAccessRightsError(AccessRightsError):
    pass


def init_schema(con_uri):

    with text_resource_stream('schema.sql', 'pypnusershub.db') as sql_file:
        sql = sql_file.read()

    engine = create_engine(con_uri)
    with engine.connect():
        engine.execute(sql)
        engine.execute("COMMIT")


def delete_schema(con_uri):

    engine = create_engine(con_uri)
    with engine.connect():
        engine.execute("DROP SCHEMA IF EXISTS utilisateurs CASCADE")
        engine.execute("COMMIT")


def reset_schema(con_uri):
    delete_schema(con_uri)
    init_schema(con_uri)


def load_fixtures(con_uri):
    with text_resource_stream('fixtures.sql', 'pypnusershub.db') as sql_file:

        engine = create_engine(con_uri)
        with engine.connect():
            for line in sql_file:
                if line.strip():
                    engine.execute(line)
            engine.execute("COMMIT")


def user_from_token(token, secret_key=None):
    """Given a, authentification token, return the matching AppUser instance"""

    secret_key = secret_key or current_app.config['SECRET_KEY']

    try:
        s = Serializer(current_app.config['SECRET_KEY'])
        data = s.loads(token)

        id_role = data['id_role']
        id_app = data['id_application']
        return (models.AppUser
                      .query
                      .filter(models.AppUser.id_role == id_role)
                      .filter(models.AppUser.id_application == id_app)
                      .one())

    except NoResultFound:
        raise UnreadableAccessRightsError(
            'No user withd id "{}" for app "{}"'.format(id_role, id_app)
        )
    except SignatureExpired:
        raise AccessRightsExpiredError("Token expired")

    except BadSignature:
        raise UnreadableAccessRightsError('Token BadSignature', 403)


def user_from_token_foraction(token, action, secret_key=None):

    secret_key = secret_key or current_app.config['SECRET_KEY']

    try:
        s = Serializer(current_app.config['SECRET_KEY'])
        data = s.loads(token)

        id_role = data['id_role']
        id_app = data['id_application']

        return (models.VUsersactionForallGnModules
                  .query
                  .filter(models.VUsersactionForallGnModules.id_role == id_role)
                  .filter(models.VUsersactionForallGnModules.id_application == id_app)
                  .filter(models.VUsersactionForallGnModules.tag_action_code == action)
                  .first())

    except NoResultFound:
        raise UnreadableAccessRightsError(
            'No user withd id "{}" for app "{}"'.format(id_role, id_app)
        )
    except SignatureExpired:
        raise AccessRightsExpiredError("Token expired")

    except BadSignature:
        raise UnreadableAccessRightsError('Token BadSignature', 403)
