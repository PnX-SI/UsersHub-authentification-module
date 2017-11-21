# coding: utf8

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)


'''
routes relatives aux application, utilisateurs et à l'authentification
'''

import json

import datetime
from functools import wraps

from flask import Blueprint, request, Response, current_app, redirect, g

from sqlalchemy.orm import exc

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from pypnusershub.db import models
from pypnusershub.db.tools import (
    user_from_token, user_from_token_foraction,
    UnreadableAccessRightsError,
    AccessRightsExpiredError
)


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
        cookie_autorenew = app.config.get('COOKIE_AUTORENEW', True)

        if cookie_autorenew:

            @app.after_request
            def after_request(response):
                try:
                    set_cookie = response.headers.get('Set-Cookie', '')
                    is_setting_token = set_cookie.startswith('token=')
                    is_token_set = request.cookies.get('token')
                    if is_token_set and not is_setting_token:
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


def check_auth(
    level,
    get_role=False,
    redirect_on_expiration=None,
    redirect_on_invalid_token=None,
):
    def _check_auth(fn):
        @wraps(fn)
        def __check_auth(*args, **kwargs):
            try:
                # TODO: better name and configurability for the token
                user = user_from_token(request.cookies['token'])

                if user.id_droit_max < level:
                    # TODO: english error message ?
                    print('Niveau de droit insufissants')
                    return Response('Forbidden', 403)

                if get_role:
                    kwargs['id_role'] = user.id_role

                g.user = user

                return fn(*args, **kwargs)

            except AccessRightsExpiredError:
                print('expired')  # TODO: turn prints into logging
                if redirect_on_expiration:
                    res = redirect(redirect_on_expiration, code=302)
                    res.set_cookie('token', '', expires=0)
                    return res
                return Response('Token Expired', 403)

            except KeyError as e:
                if 'token' not in e.args:
                    raise
                if redirect_on_expiration:
                    return redirect(redirect_on_expiration, code=302)
                return Response('No token', 403)

            except UnreadableAccessRightsError:
                print('BadSignature')
                # invalid token,
                if redirect_on_invalid_token:
                    res = redirect(redirect_on_invalid_token, code=302)
                    res.set_cookie('token', '', expires=0)
                    return res
                return Response('Token BadSignature', 403)

            except Exception as e:
                trap_all_exceptions = current_app.config.get(
                    'TRAP_ALL_EXCEPTIONS',
                    True
                )
                if not trap_all_exceptions:
                    raise
                print('Exception')
                print(e)
                msg = json.dumps({'type': 'Exception', 'msg': repr(e)})
                return Response(msg, 403)

        return __check_auth
    return _check_auth


def check_auth_cruved(
    action,
    get_role=False,
    redirect_on_expiration=None,
    redirect_on_invalid_token=None,
):
    def _check_auth_cruved(fn):
        @wraps(fn)
        def __check_auth_cruved(*args, **kwargs):
            try:
                # TODO: better name and configurability for the token

                user = user_from_token_foraction(request.cookies['token'], action)

                if (user is None):
                    print('Niveau de droit insufissants')
                    return Response('Forbidden', 403)

                if get_role:
                    kwargs['info_role'] = (user.id_role, user.max_gn_data_type)

                g.user = user

                return fn(*args, **kwargs)

            except AccessRightsExpiredError:
                print('expired')  # TODO: turn prints into logging
                if redirect_on_expiration:
                    res = redirect(redirect_on_expiration, code=302)
                    res.set_cookie('token', '', expires=0)
                    return res
                return Response('Token Expired', 403)

            except KeyError as e:
                if 'token' not in e.args:
                    raise
                if redirect_on_expiration:
                    return redirect(redirect_on_expiration, code=302)
                return Response('No token', 403)

            except UnreadableAccessRightsError:
                print('BadSignature')
                # invalid token,
                if redirect_on_invalid_token:
                    res = redirect(redirect_on_invalid_token, code=302)
                    res.set_cookie('token', '', expires=0)
                    return res
                return Response('Token BadSignature', 403)

            except Exception as e:
                trap_all_exceptions = current_app.config.get(
                    'TRAP_ALL_EXCEPTIONS',
                    True
                )
                if not trap_all_exceptions:
                    raise
                print('Exception')
                print(e)
                msg = json.dumps({'type': 'Exception', 'msg': repr(e)})
                return Response(msg, 403)

        return __check_auth_cruved
    return _check_auth_cruved


@routes.route('/login', methods=['POST'])
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

        except KeyError as e:
            parameters = ", ".join(e.args)
            msg = json.dumps({
                'type': 'login',
                'msg': 'The following parameters are required: %s' % parameters
            })
            # Initially the status code used was 490, so it's kept as a
            # default value to maintain compat. However, 400 is the
            # appropriate code and you can choose to set it
            # up that way with the BAD_LOGIN_STATUS_CODE setting.
            status_code = current_app.config.get('BAD_LOGIN_STATUS_CODE', 490)
            return Response(msg, status=status_code)

        except exc.NoResultFound as e:
            msg = json.dumps({
                'type': 'login',
                'msg': (
                    'No user found with the username "{login}" for '
                    'the application with id "{id_app}"'
                ).format(login=login, id_app=id_app)
            })
            status_code = current_app.config.get('BAD_LOGIN_STATUS_CODE', 490)
            return Response(msg, status=status_code)

        except Exception as e:
            msg = json.dumps({
                'type': 'bug',
                'msg': 'Unkown error during login'
            })
            return Response(msg, status=500)

        if not user.check_password(user_data['password']):
            msg = json.dumps({
                'type': 'password',
                'msg': 'Mot de passe invalide'
            })
            status_code = current_app.config.get('BAD_LOGIN_STATUS_CODE', 490)
            return Response(msg, status=status_code)

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


@routes.route('/logout', methods=['GET', 'POST'])
def logout():
    resp = redirect("/", code=302)
    resp.delete_cookie('token')
    return resp
