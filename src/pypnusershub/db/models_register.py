import re
import base64

from flask import current_app
from pypnusershub.db.models import check_and_encrypt_password
from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import JSONB

from .models import User


config = current_app.config

DB = current_app.config["DB"]


class TempUser(DB.Model):
    __tablename__ = "temp_users"
    __table_args__ = {"schema": "utilisateurs", "extend_existing": True}

    id_temp_user = DB.Column(DB.Integer, primary_key=True)
    token_role = DB.Column(DB.Unicode)
    password = DB.Column(DB.Unicode)
    pass_md5 = DB.Column(DB.Unicode)
    identifiant = DB.Column(DB.String(250))
    nom_role = DB.Column(DB.String(250))
    prenom_role = DB.Column(DB.String(250))
    desc_role = DB.Column(DB.String(250))
    remarques = DB.Column(DB.String(250))
    groupe = DB.Column(DB.Boolean)
    organisme = DB.Column(DB.String(250))
    id_organisme = DB.Column(DB.Integer)
    id_application = DB.Column(DB.Integer)
    email = DB.Column(DB.Unicode)
    champs_addi = DB.Column(JSONB)
    date_insert = DB.Column(DB.DateTime)
    date_update = DB.Column(DB.DateTime)

    def set_password(self, password, password_confirmation, md5):
        self.password, self.pass_md5 = check_and_encrypt_password(
            password, password_confirmation, md5
        )

    def is_valid(self):
        is_valid = True
        msg = ""

        if not self.password:
            is_valid = False
            msg += "Password is required. "

        re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$")
        if not re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", self.email):
            is_valid = False
            msg += "E-mail is not valid. "
        # check if user or temp user exist with an email or login given
        role = (
            DB.session.query(User)
            .filter(or_(User.email == self.email, User.identifiant == self.identifiant))
            .first()
        )
        if role:
            is_valid = False
            if role.email == self.email:
                msg += "Un compte avec l'email " + self.email + " existe déjà. "
            else:
                msg += (
                    "Un compte avec l'identifiant "
                    + self.identifiant
                    + " existe déjà. "
                )

        temp_role = (
            DB.session.query(TempUser)
            .filter(or_(TempUser.email == self.email, TempUser.identifiant == self.identifiant))
            .first()
        )
        if temp_role:
            is_valid = False
            if temp_role.email == self.email:
                msg += "Un compte avec l'email " + self.email + " existe déjà. "
            else:
                msg += (
                    "Un compte avec l'identifiant "
                    + self.identifiant
                    + " existe déjà. "
                )

        return (is_valid, msg)

    def as_dict(self, recursif=False, columns=(), depth=None):
        '''
            The signature of the function must be the as same the as_dict func from https://github.com/PnX-SI/Utils-Flask-SQLAlchemy
        '''
        return {
            "id_temp_user": self.id_temp_user,
            "token_role": self.token_role,
            "identifiant": self.identifiant,
            "nom_role": self.nom_role,
            "prenom_role": self.prenom_role,
            "desc_role": self.desc_role,
            "remarques": self.remarques,
            "id_organisme": self.id_organisme,
            "id_application": self.id_application,
            "organisme": self.organisme,
            "email": self.email,
            "groupe": self.groupe,
            "password": self.password,
            "pass_md5": self.pass_md5,
            "champs_addi": self.champs_addi

        }


class CorRoleToken(DB.Model):

    __tablename__ = "cor_role_token"
    __table_args__ = {"schema": "utilisateurs", "extend_existing": True}

    id_role = DB.Column(DB.Integer, primary_key=True)
    token = DB.Column(DB.Unicode)

    def as_dict(self, recursif=False, columns=(), depth=None):
        '''
            The signature of the function must be the as same the as_dict func from https://github.com/PnX-SI/Utils-Flask-SQLAlchemy
        '''
        return {"id_role": self.id_role, "token": self.token}
