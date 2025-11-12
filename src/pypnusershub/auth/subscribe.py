import random
from datetime import datetime, timedelta

from pypnusershub.schemas import UserSchema
import sqlalchemy as sa
from flask import current_app, request
from pypnusershub.db import db
from pypnusershub.db.models import (
    CorRoleToken,
    CorRoles,
    TempUser,
    User,
    UserApplicationRight,
)
from pypnusershub.db.tools import DifferentPasswordError


def generate_token():
    """
    Generate a random token of 128 bits.

    Returns
    -------
    str
        The generated token as a string of 128 bits.
    """
    return str(random.getrandbits(128))


def create_cor_role_token(email):
    """
    Create a token associated with an id_role

    Parameters
    ----------
    email : str
        email of the user

    Returns
    -------
    token : str
        token associated with the id_role
    """

    if not email:
        raise Exception("No email was found")

    user = db.session.execute(
        sa.select(User).where(User.email == email)
    ).scalar_one_or_none()

    if not user:
        raise KeyError("No user was found with the following email address : " + email)

    token = generate_token()
    # Remove old token
    db.session.execute(
        sa.delete(CorRoleToken).where(CorRoleToken.id_role == user.id_role)
    )
    # Create new token
    db.session.add(CorRoleToken(**{"id_role": user.id_role, "token": token}))
    db.session.commit()

    return {"token": token, "id_role": user.id_role, "role": user.as_dict()}


def create_temp_user(user_data):
    """
    Create a temporary user in the database.

    Parameters
    ----------
    user_data : dict
        data of the user to be created

    Returns
    -------
    token : str
        token associated with the temporary user

    Raises
    ------
    Exception
        if the password and password_confirmation are different or if the user_data is invalid
    """

    # Create new temp user
    role_data = {}
    for att in user_data:
        if hasattr(TempUser, att):
            role_data[att] = user_data[att]
    temp_user = TempUser(**role_data)

    # Encrypt and set password
    try:
        temp_user.set_password(
            user_data["password"],
            user_data["password_confirmation"],
            current_app.config["PASS_METHOD"] or current_app.config["FILL_MD5_PASS"],
        )
    except DifferentPasswordError:
        raise Exception("Password and password_confirmation are differents")

    # Check sended parameters (password, login and exiting email)
    (is_temp_user_valid, pwd_validity_msg) = temp_user.is_valid()

    if not is_temp_user_valid:
        raise Exception(pwd_validity_msg)

    # Delete duplicate entries
    db.session.execute(
        sa.delete(TempUser).where(TempUser.identifiant == temp_user.identifiant)
    )

    # Delete old entries (cleaning)
    days = 7 if not "AUTO_ACCOUNT_DELETION_DAYS" in current_app.config else 7
    db.session.execute(
        sa.delete(TempUser).where(
            TempUser.date_insert <= (datetime.now() - timedelta(days=days))
        )
    )
    # Update attributes
    temp_user.token_role = generate_token()

    # Save new temp user in database
    db.session.add(temp_user)

    db.session.commit()

    return {"token": temp_user.token_role}


def valid_temp_user(data: dict):
    """
    Route pour valider un compte temporaire et en faire un utilisateur
    (requete a usershub).
    """

    token = data["token"]
    id_application = data["id_application"]

    # recherche de l'utilisateur temporaire correspondant au token
    temp_user = db.session.execute(
        sa.select(TempUser).where(TempUser.token_role == token)
    ).scalar_one_or_none()
    if not temp_user:
        raise Exception(
            f"""
            Il n'y a pas d'utilisateur temporaire correspondant au token fourni {token}.<br>
            Il se peut que la requête de création de compte ai déjà été validée, ou bien que l'adresse de validation soit erronée.<br>
            """
        )

    req_data = temp_user.as_dict()

    # Récupération du groupe par défaut
    id_grp = UserApplicationRight.get_default_for_app(id_application).id_role
    if not id_grp:
        raise ValueError("Pas de groupe par défaut pour l'application")

    # set password correctly
    req_data["_password_plus"] = req_data["password"]
    req_data["_password"] = req_data["pass_md5"]
    role_data = {"active": True}
    for att in req_data:
        if hasattr(User, att):
            if att == "organisme":
                continue
            # Patch pas beau pour corriger le db.Unicode de TRole pour id_organisme
            if att == "id_organisme" and req_data[att] == "None":
                role_data[att] = None
            else:
                role_data[att] = req_data[att]
    role = User(**role_data)

    db.session.add(role)
    db.session.commit()

    # Ajout du role au profil
    cor = CorRoles(id_role_groupe=id_grp, id_role_utilisateur=role.id_role)
    db.session.add(cor)

    db.session.delete(temp_user)
    db.session.commit()

    return role.as_dict()


def change_password(token: str, password: str, password_confirmation: str):
    """
    Route permettant à un utilisateur de renouveler
    son mot de passe
    """

    if not token:
        raise ValueError("Token non défini dans paramètre POST")

    if not password_confirmation or not password:
        raise ValueError("Password non défini dans paramètres POST")

    associated_id_role = db.session.scalar(
        sa.select(CorRoleToken.id_role).where(CorRoleToken.token == token)
    )
    if not associated_id_role:
        raise ValueError("Pas d'id role associée au token")

    role = db.session.get(User, associated_id_role)

    if not role:
        raise ValueError("Pas d'utilisateur correspondant à id_role")
    if not password == password_confirmation:
        raise ValueError("Les deux mots de passes ne correspondent pas")
    role.password = password
    db.session.commit()

    # delete cors
    db.session.query(CorRoleToken).filter(CorRoleToken.token == token).delete()
    db.session.commit()

    return role.as_dict()
