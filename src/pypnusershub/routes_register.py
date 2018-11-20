# fichier contenant les route pour faire des appels à UsersHub
#
# - en se connectant en tant que qu'adminisatrateur de l'application courrante
# --  qui est utilisateur de USERHUB avec des droits suffisants pour creer des utilisateur
# --  pour cela il faut renseigner dans la configuration
# --
#
# - pour creer des nouveaux utilisateurs
#
# - pour changer les mots de passe
#
# - pour éditer les droits des utilisateurs
#
# - etc..

import json

import requests

from flask_mail import Message

from flask import (
    Blueprint,
    request,
    render_template,
    url_for,
    session,
    redirect
)



from functools import wraps

from .db.models import Application, User, UserApplicationRight

from flask import current_app

# from .utils_register import connect_usershub, req_json_or_text
# from .routes import check_auth


config = current_app.config

DB = config.get('DB', None)

MAIL = config.get('MAIL', None)

s = requests.Session()

bp = Blueprint('register', __name__)


def get_json_request(r):

    try:
        r_json = r.json()
    except Exception:
        r_json = None

    return r_json


def req_json_or_text(r, msg_pypn=""):
    '''
        revoie r.json si possible
        r.text sinon
    '''
    r_json = get_json_request(r)

    if not r_json:

        return msg_pypn + " : " + r.text, r.status_code

    if msg_pypn:

        r_json['msg_pypn'] = msg_pypn

    return json.dumps(r_json), r.status_code


def connect_admin():
    '''
        decorateur pour la connexion de l'admin a une appli
        ici url sans / à la fin
    '''
    def _connect_admin(f):
        @wraps(f)
        def __connect_admin(*args, **kwargs):
            # connexion à usershub

            id_app_usershub = DB.session.query(Application.id_application).filter(Application.nom_application == 'UsersHub').first()[0]

            if not id_app_usershub:

                return "Pas d'id app usersHub", 500

            # test si on est déjà connecté
            r = s.post(config['URL_USERHUB'] + "/routes_register/test_connexion")
            b_connexion = (r.status_code == 200)

            # si on est pas connecté on se connecte
            if not b_connexion:
                # connexion à usershub
                r = s.post(config['URL_USERHUB'] + "/" + "pypn/auth/login", json={'login': config['ADMIN_APPLICATION_LOGIN'], 'password': config['ADMIN_APPLICATION_PASSWORD'], 'id_application': id_app_usershub})

            # si echec de connexion
            if r.status_code != 200:

                return req_json_or_text(r, "Problème de connexion à usershub"), r.status_code

            return f(*args, **kwargs)

        return __connect_admin

    return _connect_admin


@bp.route('test_uh', methods=['GET'])
@connect_admin()
def test():

    r = s.post(config['URL_USERHUB'] + "/api_register/test_connexion")

    return req_json_or_text(r, "Test pypn")


# route generiques a sécuriser avec crsf ?
@bp.route("post_usershub/<string:type_req>", methods=['POST'])
@connect_admin()
def post_usershub(type_req):

    # test pour savoir qui peut quoi
    dict_type_rect_droit = {
        'test_connexion': 0,
        'valid_temp_user': 0,
        'create_temp_user': 0,
        'change_password': 0,
        'create_cor_role_token': 0,
        'add_application_right_to_role': 0,

        'update_user': 1,

        'change_application_right': 4,
        # 'delete_user': 6, ??
    }

    id_droit = 0

    if session.get('current_user', None):

        id_role = session['current_user']['id_role']

        id_droit = DB.session.query(UserApplicationRight.id_droit)\
            .filter(UserApplicationRight.id_role == id_role)\
            .filter(UserApplicationRight.id_application == config['ID_APP']).one()[0]

    id_droit_type_req = dict_type_rect_droit.get(type_req, 7)

    if not id_droit >= id_droit_type_req:

        return "Droits insuffisant pour la requête usershub : " + type_req, 400

    # les test de paramètres seront faits ds usershub
    data = request.get_json()

    url = config['URL_USERHUB'] + "/" + "api_register/" + type_req

    r_usershub = s.post(url, json=data)

    # after request definir route dans app
    # par ex. pour les mails1
    if r_usershub.status_code == 200:

        r_after = after_request(type_req, get_json_request(r_usershub))

        print("r_after", r_after)

        if r_after != 0:
            if r_after['msg'] != "ok":
                print("erreur r_after")
                return json.dumps({'msg': 'Problème after request pour post_usershub ' + type_req, 'msg_after': req_json_or_text(r_after)}), r_after.status_code

    return req_json_or_text(r_usershub)


def after_request(type_req, data):

    after_request_dict = config.get('after_USERSHUB_request', None)

    if not after_request_dict:

        return 0

    f = after_request_dict.get(type_req, None)

    if not f:

        return 0

    return f(data)
