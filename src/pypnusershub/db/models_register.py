from flask import current_app

from app.utils.utilssqlalchemy import (
    serializable
)

from .model import User

from Crypto.Cipher import XOR

import base64

import re

config = current_app.config

DB = current_app.config['DB']


def encrypt_str(s, secret_key):

    return s


def decrypt_str(s, secret_key):

    return s


@serializable
class TempUser(DB.Model):
    __tablename__ = 'temp_users'
    __table_args__ = {'schema': 'utilisateurs', 'extend_existing': True}

    id_temp_user = DB.Column(DB.Integer, primary_key=True)
    token_role = DB.Column(DB.Unicode)
    password = DB.Column(DB.Unicode)
    password_confirmation = DB.Column(DB.Unicode)
    identifiant = DB.Column(DB.String(250))
    nom_role = DB.Column(DB.String(250))
    prenom_role = DB.Column(DB.String(250))
    desc_role = DB.Column(DB.String(250))
    remarques = DB.Column(DB.String(250))
    groupe = DB.Column(DB.Boolean)
    pn = DB.Column(DB.Boolean)
    id_unite = DB.Column(DB.Integer)
    id_organisme = DB.Column(DB.Integer)
    organisme = DB.Column(DB.String(250))
    email = DB.Column(DB.Unicode)
    date_insert = DB.Column(DB.DateTime)
    date_update = DB.Column(DB.DateTime)

    def encrypt_password(self, secret_key):

        self.password = encrypt_str(self.password, secret_key)
        self.password_confirmation = encrypt_str(self.password_confirmation, secret_key)

    def decrypt_password(self, secret_key):

        self.password = decrypt_str(self.password, secret_key)
        self.password_confirmation = decrypt_str(self.password_confirmation, secret_key)

    def is_valid(self):

        is_valid = True
        msg = ""

        if not self.password:

            is_valid = False
            msg += "password is required.\n"

        if self.password != self.password_confirmation:

            msg += "password and password_confirmation are differents.\n"
            is_valid = False

        re.compile(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$")

        if not re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", self.email):

            msg += "email is not valid.\n"
            is_valid = False

        role = DB.session.query(User).filter(User.email == self.email).first()

        if role:

            msg += "user with mail " + self.email + " exists"

        return (is_valid, msg)


@serializable
class CorRoleToken(DB.Model):

    __tablename__ = 'cor_role_token'
    __table_args__ = {'schema': 'utilisateurs', 'extend_existing': True}

    id_role = DB.Column(DB.Integer, primary_key=True)
    token = DB.Column(DB.Unicode)
