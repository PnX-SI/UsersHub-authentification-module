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


import requests

from flask_mail import Message

import random

from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for
)

from .db.models import Application, User

from flask import current_app

config = current_app.config

DB = config.get('DB', None)

MAIL = config.get('MAIL', None)

bp = Blueprint('register', __name__)

s = requests.Session()


def usershub_login():

    id_app_usershub = DB.session.query(Application.id_application).filter(Application.nom_application == 'UsersHub').first()[0]

    if not id_app_usershub:

        return "Pas d'id app usersHub"

    print(config.get('URL_USERHUB', None), 'aaaaaaaaa', config['URL_USERHUB'], "\n")

    # test si on est déjà connecté
    r = s.post(config['URL_USERHUB'] + "/api_register/test_connexion")

    # si on est pas connecté
    if r.status_code != 200:
        # connexion à usershub
        r = s.post(config['URL_USERHUB'] + "/" + "pypn/auth/login", json={'login': config['ADMIN_APPLICATION_LOGIN'], 'password': config['ADMIN_APPLICATION_PASSWORD'], 'id_application': id_app_usershub})

    print(r)

    return r




@bp.route('add_application_right_to_role', methods=['POST'])
def add_application_right_to_role():
    '''
        route pour faire une requete a l'application Usershub pour ajouter des droits à un utilisateur
    '''
    data = request.get_json()

    # connexion à userhub
    r = usershub_login()

    if not r.status_code == 200:

        return "problème de connexion à usershub : " + r.text, r.status_code

    # requete pour ajouter les droits
    r = s.post(config.URL_USERHUB + "/" + "api_register/add_application_right_to_role", json=data)

    return r.text, r.status_code


@bp.route('create_temp_user', methods=['POST'])
def create_temp_user():
    '''
        route pour creer un compte temporaire en attendait la confirmation de l'adresse mail
        les mot de passe seront stocké en crypté
        1. on stocke les variables qui seront utilisées par la création de compte
        2. on envoie un mail pour demander la confirmation du compte mail
    '''

    # a mettre dans usershub

    # recuperation des parametres
    data = request.get_json()

    if not data.get("email", None):

        return "email non reseigné dans les paramètres", 412

    # tests? sachant que se sera fait dans userhub

    # connexion à userhub
    r = usershub_login()

    if not r.status_code == 200:

        return "problème de connexion à usershub : " + r.text, r.status_code

    # requete pour la create d'utilisateur temporaires
    r = s.post(config.URL_USERHUB + "/" + "api_register/create_temp_user", json=data)

    if not r.status_code == 200:

        return "erreur dans la requete à userhub de création d'utilisateur temporaire : " + r.text, r.status_code

    if(MAIL):

        token_role = r.json().get('token_role')

        email = data['email']

        url_validation = config.URL_APPLICATION + '/api/user/valid_temp_user/' + temp_user.token_role

        with MAIL.connect() as conn:

            msg = Message(
                '[OEASC] Votre demande de création de compte à bien été prise en compte',
                sender=config.DEFAULT_MAIL_SENDER,
                recipients=[temp_user.email])
            msg.html = render_template('modules/oeasc/mail/demande_validation_compte.html', url_validation=url_validation)

            conn.send(msg)

    return 'Un mail de verification de compte vous a été envoyé. Veuillez cliquer sur le lien de confirmation dans l''email afin de valider votre compte'


@bp.route('valid_temp_user/<string:temp_user_token>', methods=['GET'])
def valid_temp_user(temp_user_token):
    '''
        route pour valider un compte temporire et en faire un utilisateur (requete a userbub)
    '''
    r = usershub_login()

    if not r.status_code == 200:

        return "problème de connexion à usershub : " + r.text, r.status_code

    data['token_role'] = temp_user_token
    data["applications"] = [
        {
            "id_app": config.ID_APP,
            "id_droit": 1
        }
    ]

    r = s.post(config.URL_USERHUB + "/" + "api_register/valid_temp_user", json=data)

    if r.status_code != 200:

        return 'erreur dans la validation de compte temporaire : ' + r.text, r.status_code

    role = r.json()
    identifiant = r['identifiant']

    return redirect(url_for('oeasc.login', identifiant=identifiant, validation_compte="valid"))


@bp.route("reset_password", methods=['POST'])
def reset_password():

    data = request.get_json()

    token = data.get('token', None)

    if not token:

        return "token non defini dans paramètre POST", 500

    password = data.get('password', None)
    password_confirmation = data.get('password_confirmation', None)

    if not password_confirmation or not password:

        return "password non defini dans paramètres POST", 500

    if not password_confirmation == password:

        return "password et password_confirmation sont différents", 500

    res = DB.session.query(CorRoleToken.id_role).filter(CorRoleToken.token == token).first()

    if not res:

        return "pas d'id role associée au token", 500

    id_role = res[0]

    data_out = {'id_role': id_role, 'password': password}

    id_app_usershub = DB.session.query(Application.id_application).filter(Application.nom_application == 'UsersHub').first()[0]
    url_usershub_login = config.URL_USERHUB + "/" + "pypn/auth/login"
    r = s.post(url_usershub_login, json={'login': config.USER_USERHUB, 'password': config.PWD_USERHUB, 'id_application': id_app_usershub})

    print("login", r.text, r.status_code)

    r = s.post(config.URL_USERHUB + "/" + "api_register/change_password", json=data_out)

    # delete cors
    DB.session.query(CorRoleToken.id_role).filter(CorRoleToken.token == token).delete()
    DB.session.commit()

    print("chgpwd", r.text, r.status_code, config.URL_USERHUB + "/" + "api_register/change_password")

    return r.text, r.status_code


@bp.route("reset_password_send_mail", methods=['POST'])
def reset_password_send_mail():

    data = request.get_json()

    email = data.get('email')

    # si email on envoie un mail
    if not email:

        return "Email non renseigné", 500

    role = DB.session.query(User).filter(User.email == email).first()

    if not role:

        return "Pas d'utilisateur pour l'email " + email, 500

    r = s.requests(config.URL_USERHUB + "/" + "api_register/create_cor_role_token")

    if not r.status_code == 200:

        return "erreur dans la requete a USERHUB : " + r.text, r.status_code

    token = r.json()['token']

    if MAIL:

        with MAIL.connect() as conn:

            msg = Message(
                '[OEASC] Changement de mot de passe',
                sender=config.DEFAULT_MAIL_SENDER,
                recipients=[role.email])
            msg.html = render_template('modules/oeasc/mail/changement_de_mot_de_passe.html', url_validation=url_validation)

            conn.send(msg)

    return "ok", 200
