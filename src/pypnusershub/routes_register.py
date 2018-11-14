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

s = requests.Session()

bp = Blueprint('register', __name__)


def change_password_default_template(url_validation):

    return "<p>Veuillez cliquer sur ce lien afin de pouvoir " + \
        "<a href=" + url_validation + " > modifier votre mot de passe.</a></p>"


def usershub_login():

    id_app_usershub = DB.session.query(Application.id_application).filter(Application.nom_application == 'UsersHub').first()[0]

    if not id_app_usershub:

        return "Pas d'id app usersHub"

    # test si on est déjà connecté
    r = s.post(config['URL_USERHUB'] + "/api_register/test_connexion")

    # si on est pas connecté
    if r.status_code != 200:
        # connexion à usershub
        r = s.post(config['URL_USERHUB'] + "/" + "pypn/auth/login", json={'login': config['ADMIN_APPLICATION_LOGIN'], 'password': config['ADMIN_APPLICATION_PASSWORD'], 'id_application': id_app_usershub})

    return r


@bp.route('test', methods=['GET'])
def test():

    r = usershub_login()

    print(r.text, r.status_code)

    return r.text, r.status_code


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
    r = s.post(config['URL_USERHUB'] + "/" + "api_register/add_application_right_to_role", json=data)

    return json.dumps({'msg': r.text}), r.status_code


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
    r = s.post(config['URL_USERHUB'] + "/" + "api_register/create_temp_user", json=data)

    if not r.status_code == 200:

        return "erreur dans la requete à userhub de création d'utilisateur temporaire : " + r.text, r.status_code

    if not MAIL and config.get('ANIMATEUR_APPLICATION_MAIL', None):

        return "les paramètres d'envoie de mail ne sont pas correctement définis", 500

    token = r.json().get('token')

    email = data['email']

    url_validation = config['URL_APPLICATION'] + url_for('register.valid_temp_user', token=token)

    application = DB.session.query(Application).filter(Application.id_application == config['ID_APP']).one()

    with MAIL.connect() as conn:

        msg = Message(
            '[' + application.nom_application + '] demande de création de compte',
            sender=config['ANIMATEUR_APPLICATION_MAIL'],
            recipients=[email])

        template = config.get('template_demande_validation_compte', None)

        if(template):

            msg.html = render_template(
                template,
                url_validation=url_validation,
                identifiant=data['identifiant'],
                config=config
            )

        else:

            msg.html = "<p>Veuillez cliquer sur ce lien pour " + \
                "<a href=" + {{url_validation}} + "> valider votre inscription</a> " + \
                "puis vous connecter au site afin de valider votre inscription.</p>"

        conn.send(msg)

    return json.dumps({'msg': 'Un mail de verification de compte vous a été envoyé. Veuillez cliquer sur le lien de confirmation dans l''email afin de valider votre compte'}), 200


@bp.route('valid_temp_user/<string:token>', methods=['GET'])
def valid_temp_user(token):
    '''
        route pour valider un compte temporire et en faire un utilisateur (requete a userbub)
    '''

    r = usershub_login()

    if not r.status_code == 200:

        return "problème de connexion à usershub : " + r.text, r.status_code

    data = {
        'token': token,
        'id_application': config['ID_APP'],
        'id_droit': 1,
    }

    r = s.post(config['URL_USERHUB'] + "/" + "api_register/valid_temp_user", json=data)

    if r.status_code != 200:

        return 'erreur dans la validation de compte temporaire : ' + r.text, r.status_code

    role = r.json()
    identifiant = role['identifiant']

    f_url = config.get('redirect_on_valid_temp_user', None)

    if f_url:

        url_redirect = f_url({'identifiant': identifiant})

    else:

        url_redirect = config['URL_APPLICATION']

    application = DB.session.query(Application).filter(Application.id_application == config['ID_APP']).one()

    with MAIL.connect() as conn:

        msg = Message(
            '[' + application.nom_application + '] [ANIMATEUR] création d'' un nouvel utilisateur',
            sender=config['ANIMATEUR_APPLICATION_MAIL'],
            recipients=[config['ANIMATEUR_APPLICATION_MAIL'], config['ADMIN_APPLICATION_MAIL']])

        msg_html = "<p>Un nouvel utilisateur viens de s'enregister</p><p>Identifiant : {}</p><p>Nom : {}</p><p>Prenom : {}</p><p>Organisme : {}</p>".format(
            role['identifiant'].strip(),
            role['email'].strip(),
            role['nom_role'].strip(),
            role['prenom_role'].strip(),
            role['organisme'].strip()
        )

        print(msg_html)

        msg.html = msg_html

        conn.send(msg)

    return redirect(url_redirect)


@bp.route("change_password", methods=['POST'])
def change_password():

    data = request.get_json()

    r = usershub_login()

    if not r.status_code == 200:

        return "problème de connexion à usershub : " + r.text, r.status_code

    r = s.post(config['URL_USERHUB'] + "/" + "api_register/change_password", json=data)

    if r.status_code != 200:

        return "Erreur : " + r.text, r.status_code

    user = r.json()
    identifiant = user['identifiant']

    return json.dumps({'identifiant': identifiant})
    # return redirect(url_for('oeasc.login', identifiant=identifiant))


@bp.route("change_password_send_mail", methods=['POST'])
def change_password_send_mail():

    r = usershub_login()

    if not r.status_code == 200:

        return "problème de connexion à usershub : " + r.text, r.status_code

    data = request.get_json()

    email = data.get('email')

    # si email on envoie un mail
    if not email:

        return "Email non renseigné", 500

    role = DB.session.query(User).filter(User.email == email).first()

    if not role:

        return "Pas d'utilisateur pour l'email " + email, 500

    r = s.post(config['URL_USERHUB'] + "/" + "api_register/create_cor_role_token", json={'id_role': role.id_role})

    if not r.status_code == 200:

        return "erreur dans la requete a USERHUB : " + r.text, r.status_code

    token = r.json()['token']

    if not MAIL and config.get('ANIMATEUR_APPLICATION_MAIL', None):

        return "les paramètres d'envoie de mail ne sont pas correctement définis", 500

    application = DB.session.query(Application).filter(Application.id_application == config['ID_APP']).one()

    # TODO Trouver une solution rendre cet url generique
    # url_validation = config['URL_APPLICATION'] + "/oeasc/change_password/" + token
    url_validation = config['URL_APPLICATION'] + "/" + url_for(config['url_change_password'], token=token)

    with MAIL.connect() as conn:

        msg = Message(
            '[' + application.nom_application + '] changement de mot de passe',
            sender=config['ANIMATEUR_APPLICATION_MAIL'],
            recipients=[role.email])

        template = config.get('template_change_password', None)

        if(template):

            msg.html = render_template(template, url_validation=url_validation)

        else:

            msg.html = "<p>Veuillez cliquer sur ce lien afin de pouvoir " + \
                "<a href=" + {{url_validation}} + " > modifier votre mot de passe.</a></p>"

        conn.send(msg)

    return json.dumps({"msg": "ok"}), 200
