from flask import current_app


from .models import User
from pypnusershub.db.models import encrypt_password

import base64

import re

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
    pn = DB.Column(DB.Boolean)
    id_organisme = DB.Column(DB.Integer)
    organisme = DB.Column(DB.String(250))
    email = DB.Column(DB.Unicode)
    date_insert = DB.Column(DB.DateTime)
    date_update = DB.Column(DB.DateTime)

    def encrypt_password(self, password, password_confirmation, md5):
        self.password, self.pass_md5 = encrypt_password(
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

        role = DB.session.query(User).filter(User.email == self.email).first()

        if role:
            is_valid = False
            msg += "User with mail " + self.email + " exists. "

        return (is_valid, msg)

    def as_dict(self, recursif=False, columns=()):
        return {
            "id_temp_user": self.id_temp_user,
            "token_role": self.token_role,
            "identifiant": self.identifiant,
            "nom_role": self.nom_role,
            "prenom_role": self.prenom_role,
            "desc_role": self.prenom_role,
            "remarques": self.prenom_role,
            "id_organisme": str(self.id_organisme),
            "organisme": self.organisme,
            "email": self.email,
            "groupe": self.groupe,
            "password": self.password,
            "pass_md5": self.pass_md5,
        }


class CorRoleToken(DB.Model):

    __tablename__ = "cor_role_token"
    __table_args__ = {"schema": "utilisateurs", "extend_existing": True}

    id_role = DB.Column(DB.Integer, primary_key=True)
    token = DB.Column(DB.Unicode)

    def as_dict(self, recursif=False, columns=()):
        return {"id_role": self.id_role, "token": self.token}
