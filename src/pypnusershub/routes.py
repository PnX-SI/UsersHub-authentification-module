# coding: utf8

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)


'''
routes relatives aux application, utilisateurs et à l'authentification
'''

import json
import datetime
from functools import wraps
from flask import Blueprint, request, Response, current_app

from pypnusershub.db import models
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer,
                          SignatureExpired, BadSignature)


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

    def register(self, app, options, first_registration=False):

        # set cookie autorenew
        expiration = app.config.get('COOKIE_EXPIRATION', 3600)
        cookie_autorenew = app.config.get('COOKIE_AUTORENEW', False)

        if cookie_autorenew:

            @app.after_request
            def after_request(response):
                try:
                    if 'token' in request.cookies:
                        cookie_exp = datetime.datetime.utcnow()
                        cookie_exp += datetime.timedelta(seconds=expiration)
                        response.set_cookie('token',
                                            request.cookies['token'],
                                            expires=cookie_exp)
                        response.set_cookie('currentUser',
                                            request.cookies['currentUser'],
                                            expires=cookie_exp)
                    return response
                # TODO: replace the generic exception by a specific one
                except Exception:
                    return response

        # register db
        init_app_with_db = app.config.get('INIT_APP_WITH_DB', False)
        if init_app_with_db:
            models.db.init_app(app)

        parent = super(ConfigurableBlueprint, self)
        parent.register(app, options, first_registration)


routes = ConfigurableBlueprint('auth', __name__)


def check_auth(level, get_role=False):
    def _check_auth(fn):
        @wraps(fn)
        def __check_auth(*args, **kwargs):
            try:
                s = Serializer(current_app.config['SECRET_KEY'])
                data = s.loads(request.cookies['token'])

                id_role = data['id_role']
                id_app = data['id_application']
                user = (models.AppUser
                              .query
                              .filter(models.AppUser.id_role == id_role)
                              .filter(models.AppUser.id_application == id_app)
                              .one())

                if user.id_droit_max < level:
                    print('Niveau de droit insufissants')
                    return Response('Forbidden', 403)

                if get_role:
                    kwargs['id_role'] = user.id_role

                return fn(*args, **kwargs)

            except SignatureExpired:
                print('expired')  # TODO: turn prints into logging
                # valid token, but expired
                return Response('Token Expired', 403)

            except BadSignature:
                print('BadSignature')
                # invalid token,
                return Response('Token BadSignature', 403)

            except Exception as e:
                print('Exception')
                print(e)
                msg = json.dumps({'type': 'Exception', 'msg': repr(e)})
                return Response(msg, 403)

        return __check_auth
    return _check_auth


@routes.route('/login', methods= ['POST'])
def login():
    try:
        user_data = request.json

        try:

            id_app = user_data['id_application']
            login = user_data['login']
            user = (models.AppUser
                          .query
                          .filter(models.AppUser.identifiant == login)
                          .filter(models.AppUser.id_application == id_app)
                          .one())

        # TODO: replace this generic exception with specific ones.
        # With this current setup, we can't tell the user if his credential
        # are invalid or if we have a bug. Any bug would trigger the display of
        # "invalid identifiers".
        except Exception as e:
            msg = json.dumps({'type': 'login', 'msg': 'Identifiant invalide'})
            return Response(json.dumps(msg, status=490))

        if not user.check_password(user_data['password']):
            msg = json.dumps({'type': 'password',
                              'msg': 'Mot de passe invalide'})
            return Response(json.dumps(msg, status=490))

        # Génération d'un token
        expiration = current_app.config['COOKIE_EXPIRATION']
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        token = s.dumps(user.as_dict())
        cookie_exp = datetime.datetime.utcnow()
        cookie_exp += datetime.timedelta(seconds=expiration)
        resp = Response(json.dumps({'user': user.as_dict(),
                                    'expires': str(cookie_exp)}))
        resp.set_cookie('token', token, expires=cookie_exp)

        return resp
    except Exception as e:
        msg = json.dumps({'login': False, 'msg': repr(e)})
        return Response(msg, status=403)
