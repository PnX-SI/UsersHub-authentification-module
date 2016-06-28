#coding: utf8

'''
routes relatives aux application, utilisateurs et à l'authentification
'''

import json
import uuid
import datetime
from functools import wraps
from flask import Blueprint, Flask, request, jsonify, session, g, Response
from server import db,init_app
from . import models
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired, BadSignature

routes = Blueprint('auth', __name__)


def check_auth(level):
    def _check_auth(fn):
        @wraps(fn)
        def __check_auth(*args, **kwargs):
            print('check auth')
            try:
                s = Serializer(init_app().config['SECRET_KEY'])
                data = s.loads(request.cookies['token'])

                user = models.AppUser.query\
                    .filter(models.AppUser.id_role==data['id_role'])\
                    .filter(models.AppUser.id_application==data['id_application'])\
                    .one()
                if user.id_droit_max < level:
                    print('Niveau de droit insufissants')
                    return Response('Forbidden', 403)

                return fn(*args, **kwargs)
            except SignatureExpired:
                print('expired')
                return Response('Token Expired', 403) # valid token, but expired
            except BadSignature:
                print('BadSignature')
                return Response('Token BadSignature', 403) # valid token, but expired
            except Exception as e:
                print('Exception')
                print(e)
                return Response('Forbidden', 403)
        return __check_auth
    return _check_auth


@routes.route('/login', methods=['POST'])
def login():
    try:
        user_data = request.json
        try :
            user = models.AppUser.query\
                .filter(models.AppUser.identifiant==user_data['login'])\
                .filter(models.AppUser.id_application==user_data['id_application'])\
                .one()
        except Exception as e:
            resp = Response(json.dumps({'type':'login', 'msg':'Identifiant invalide'}), status=490)
            return resp

        if not user.check_password(user_data['password']):
            resp = Response(json.dumps({'type':'password', 'msg':'Mot de passe invalide'}), status=490)
            return resp

        #Génération d'un token
        s = Serializer(init_app().config['SECRET_KEY'], expires_in = init_app().config['COOKIE_EXPIRATION'])
        token = s.dumps({'id_role':user.id_role})
        cookie_exp = datetime.datetime.now() + datetime.timedelta(seconds= init_app().config['COOKIE_EXPIRATION'])

        resp = Response(json.dumps({'user':user.as_dict(), 'expires':str(cookie_exp)}))
        resp.set_cookie('token', token, expires=cookie_exp)

        return resp
    except Exception as e:
        print(e)
        resp = Response(json.dumps({'login': False}), status=403)
        return resp
