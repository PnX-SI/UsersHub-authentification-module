# coding: utf8

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)
"""
    DB tools not related to any model in particular.
"""

from flask import current_app

from sqlalchemy.orm.exc import NoResultFound
import sqlalchemy as sa

from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
                          SignatureExpired, BadSignature)

from pypnusershub.db import models, db
from pypnusershub.utils import text_resource_stream


class AccessRightsError(Exception):
    pass

class CruvedImplementationError(Exception):
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

    engine = sa.create_engine(con_uri)
    with engine.connect():
        engine.execute(sql)
        engine.execute("COMMIT")


def delete_schema(con_uri):

    engine = sa.create_engine(con_uri)
    with engine.connect():
        engine.execute("DROP SCHEMA IF EXISTS utilisateurs CASCADE")
        engine.execute("COMMIT")


def reset_schema(con_uri):
    delete_schema(con_uri)
    init_schema(con_uri)


def load_fixtures(con_uri):
    with text_resource_stream('fixtures.sql', 'pypnusershub.db') as sql_file:

        engine = sa.create_engine(con_uri)
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


def user_from_token_foraction(token, action, id_app, secret_key=None):
    secret_key = secret_key or current_app.config['SECRET_KEY']

    try:
        s = Serializer(current_app.config['SECRET_KEY'])
        data = s.loads(token)

        id_role = data['id_role']
        id_app_parent = data['id_application']

        ors = [models.VUsersactionForallGnModules.id_application == id_app_parent]
        q = (
            models.VUsersactionForallGnModules
                .query
                .filter(models.VUsersactionForallGnModules.id_role == id_role)
                .filter(models.VUsersactionForallGnModules.tag_action_code == action)
        )
        if id_app:
            ors.append(models.VUsersactionForallGnModules.id_application == id_app['id_application'])

        user_cruved = q.filter(sa.or_(*ors))

        for user in user_cruved:
            if user.id_application == id_app:
                return user
            else:
                parent_app_user = user
        return parent_app_user

    except NoResultFound:
        raise UnreadableAccessRightsError(
            'No cruved for user with id "{}" for app "{}"'.format(id_role, id_app)
        )
    except SignatureExpired:
        raise AccessRightsExpiredError("Token expired")

    except BadSignature:
        raise UnreadableAccessRightsError('Token BadSignature', 403)

def cruved_for_user_in_app(
    id_role=None,
    id_application=None,
    id_application_parent=None
    ):
    """
    Return the user cruved for an application
    if no cruved for an app, the cruverd parent app is taken
    Child app cruved alway overright parent app cruved 
    """
    ors = [models.VUsersactionForallGnModules.id_application == id_application]
    q = (
        models.VUsersactionForallGnModules
                .query
                .filter(models.VUsersactionForallGnModules.id_role == id_role)
    )

    if id_application_parent:
        ors.append(models.VUsersactionForallGnModules.id_application == id_application_parent)

    q = q.filter(sa.or_(*ors))
    
    users_cruved = q.all()

    parent_app_cruved = {}
    child_cruved = {}

    for user_cruved in users_cruved:
        if user_cruved.id_application == id_application:
            child_cruved[user_cruved.tag_action_code] = user_cruved.tag_object_code
        else:
            parent_app_cruved[user_cruved.tag_action_code] = user_cruved.tag_object_code
    

    cruved = ['C', 'R', 'U', 'V', 'E', 'D']
    updated_cruved = {}

    for action in cruved:
        if action in child_cruved:
            updated_cruved[action] = child_cruved[action]
        elif action in parent_app_cruved:
            updated_cruved[action] = parent_app_cruved[action]
        else:
            updated_cruved[action] = '0'
    return updated_cruved



    # user_cruved_app = db.session.query(
    #     sa.func.utilisateurs.cruved_for_user_in_module(id_role, id_application)
    #     ).one_or_none()
    # if user_cruved_app[0]:
    #     user_cruved_app = user_cruved_app[0]
    #     user_cruved_app = {d['action']:d['level'] for d in user_cruved_app}
    # else:
    #     user_cruved_app = {}
    # if len(user_cruved_app) == 6:
    #         return user_cruved_app   
    # #if the cruved is not complet, get the parent cruved
    # else:
    #     try:
    #         user_cruved_parent_app = db.session.query(
    #             sa.func.utilisateurs.cruved_for_user_in_module(id_role, id_application_parent)
    #             ).one()
    #         assert user_cruved_parent_app[0] is not None
    #     except AssertionError:
    #             raise CruvedImplementationError("No Cruved definition for parent app")
        
    #     user_cruved_parent_app = {d['action']:d['level'] for d in user_cruved_parent_app[0]}
    #     updated_cruved = {}
    #     cruved = ['C', 'R', 'U', 'V', 'E', 'D']

    #     for action in cruved:
    #         if action in user_cruved_app:
    #             updated_cruved[action] = user_cruved_app[action]
    #         elif action in user_cruved_parent_app:
    #             updated_cruved[action] = user_cruved_parent_app[action]
    #         else:
    #             updated_cruved[action] = '0'
    #     return updated_cruved







def get_or_fetch_user_cruved(
    session=None,
    id_role=None,
    id_application=None,
    id_application_parent=None
):
    """
        Check if the cruved is in the session
        if not, get the cruved from the DB with 
        cruved_for_user_in_app()
    """
    str_id_app = str(id_application)
    if str_id_app in session and 'user_cruved' in session[str_id_app]:
        return session[str_id_app]['user_cruved']
    else:
        user_cruved = cruved_for_user_in_app(
        id_role=id_role,
        id_application=id_application,
        id_application_parent=id_application_parent
    )
        session[str_id_app] = {}
        session[str_id_app]['user_cruved'] = user_cruved
    return user_cruved




