# coding: utf8

from __future__ import unicode_literals, print_function, absolute_import, division

"""
mappings applications et utilisateurs
"""

import hashlib
import bcrypt
from bcrypt import checkpw
from os import environ
from importlib import import_module
from packaging import version

from flask_sqlalchemy import SQLAlchemy
import flask_sqlalchemy


if version.parse(flask_sqlalchemy.__version__) >= version.parse("3"):
    from flask_sqlalchemy.query import Query
else:
    from flask_sqlalchemy import BaseQuery as Query


from flask import current_app
from flask_login import UserMixin

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref
from sqlalchemy.orm.session import object_session
from sqlalchemy import Sequence, func, ForeignKey, or_
from sqlalchemy.sql import select, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, array

from pypnusershub.db.tools import NoPasswordError, DifferentPasswordError
from pypnusershub.env import db
from pypnusershub.utils import get_current_app_id

from utils_flask_sqla.serializers import serializable


def check_and_encrypt_password(password, password_confirmation, md5=False):
    if not password:
        raise NoPasswordError
    if password != password_confirmation:
        raise DifferentPasswordError
    pass_plus = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    pass_md5 = None
    if md5:
        pass_md5 = hashlib.md5(password.encode("utf-8")).hexdigest()
    return pass_plus.decode("utf-8"), pass_md5


def fn_check_password(self, pwd):
    if current_app.config["PASS_METHOD"] == "md5":
        if not self._password:
            raise ValueError("User %s has no password" % (self.identifiant))
        return self._password == hashlib.md5(pwd.encode("utf8")).hexdigest()
    elif current_app.config["PASS_METHOD"] == "hash":
        if not self._password_plus:
            raise ValueError("User %s has no password" % (self.identifiant))
        return checkpw(pwd.encode("utf8"), self._password_plus.encode("utf8"))
    else:
        raise ValueError("Undefine crypt method (PASS_METHOD)")


cor_roles = db.Table(
    "cor_roles",
    db.Column(
        "id_role_utilisateur",
        db.Integer,
        db.ForeignKey("utilisateurs.t_roles.id_role"),
        primary_key=True,
    ),
    db.Column(
        "id_role_groupe",
        db.Integer,
        db.ForeignKey("utilisateurs.t_roles.id_role"),
        primary_key=True,
    ),
    schema="utilisateurs",
    extend_existing=True,
)


class UserQuery(Query):
    def filter_by_app(self, code_app=None):
        if code_app is None:
            code_app = current_app.config["CODE_APPLICATION"]
        return (
            self.outerjoin(cor_roles, User.id_role == cor_roles.c.id_role_utilisateur)
            .outerjoin(
                UserApplicationRight,
                or_(
                    UserApplicationRight.id_role == cor_roles.c.id_role_groupe,
                    UserApplicationRight.id_role == User.id_role,
                ),
            )
            .join(
                Application,
                Application.id_application == UserApplicationRight.id_application,
            )
            .filter(Application.code_application == code_app)
        )


@serializable(exclude=["_password", "password", "_password_plus"])
class User(db.Model, UserMixin):
    __tablename__ = "t_roles"
    __table_args__ = {"schema": "utilisateurs"}
    query_class = UserQuery

    groupe = db.Column(db.Boolean, default=False)
    id_role = db.Column(
        db.Integer,
        primary_key=True,
    )

    # TODO: make that unique ?
    identifiant = db.Column(db.Unicode)
    nom_role = db.Column(db.Unicode)
    prenom_role = db.Column(db.Unicode)
    desc_role = db.Column(db.Unicode)
    _password = db.Column("pass", db.Unicode)
    _password_plus = db.Column("pass_plus", db.Unicode)
    email = db.Column(db.Unicode)
    id_organisme = db.Column(db.Integer, ForeignKey("utilisateurs.bib_organismes.id_organisme"))
    remarques = db.Column(db.Unicode)
    champs_addi = db.Column(JSONB)
    date_insert = db.Column(db.DateTime)
    date_update = db.Column(db.DateTime)
    active = db.Column(db.Boolean)
    groups = db.relationship(
        "User",
        lazy="joined",
        secondary=cor_roles,
        primaryjoin="User.id_role == utilisateurs.cor_roles.c.id_role_utilisateur",
        secondaryjoin="User.id_role == utilisateurs.cor_roles.c.id_role_groupe",
        backref=backref("members"),
    )

    @property
    def max_level_profil(self):
        q = (
            object_session(self)
            .query(func.max(Profils.code_profil))
            .select_from(User)
            .join(
                UserApplicationRight,
                or_(
                    UserApplicationRight.id_role == self.id_role,
                    UserApplicationRight.id_role.in_([role.id_role for role in self.groups]),
                ),
            )
            .join(Profils, UserApplicationRight.id_profil == Profils.id_profil)
            .filter(UserApplicationRight.id_application == get_current_app_id())
        )
        return q.scalar() or 0

    @hybrid_property
    def nom_complet(self):
        return " ".join([i for i in [self.nom_role, self.prenom_role] if i])

    @nom_complet.expression
    def nom_complet(cls):
        return db.func.array_to_string(array([cls.nom_role, cls.prenom_role]), " ")

    # applications_droits = db.relationship('AppUser', lazy='joined')
    # for Flask-Admin
    def get_id(self):
        return str(self.id_role)

    @property
    def password(self):
        if current_app.config["PASS_METHOD"] == "md5":
            return self._password
        elif current_app.config["PASS_METHOD"] == "hash":
            return self._password_plus
        else:
            raise Exception

    # TODO: change password digest algorithm for something stronger such
    # as bcrypt. This need to be done at usershub level first.
    @password.setter
    def password(self, pwd):
        pwd = pwd.encode("utf-8")
        if current_app.config["PASS_METHOD"] == "md5":
            self._password = hashlib.md5(pwd).hexdigest()
        elif current_app.config["PASS_METHOD"] == "hash":
            self._password_plus = bcrypt.hashpw(pwd, bcrypt.gensalt()).decode("utf-8")
        else:
            raise Exception("Unknown pass method")

    check_password = fn_check_password

    @property
    def is_public(self):
        return (
            current_app.config.get("PUBLIC_ACCESS_USERNAME")
            and current_app.config.get("PUBLIC_ACCESS_USERNAME") == self.identifiant
        )

    def __repr__(self):
        return "<User '{!r}' id='{}'>".format(self.identifiant, self.id_role)

    def __str__(self):
        return self.identifiant or self.nom_complet


@serializable
class Organisme(db.Model):
    __tablename__ = "bib_organismes"
    __table_args__ = {"schema": "utilisateurs"}

    id_organisme = db.Column(db.Integer, primary_key=True)
    uuid_organisme = db.Column(UUID(as_uuid=True), default=select([func.uuid_generate_v4()]))
    nom_organisme = db.Column(db.Unicode)
    adresse_organisme = db.Column(db.Unicode)
    cp_organisme = db.Column(db.Unicode)
    ville_organisme = db.Column(db.Unicode)
    tel_organisme = db.Column(db.Unicode)
    fax_organisme = db.Column(db.Unicode)
    email_organisme = db.Column(db.Unicode)
    url_organisme = db.Column(db.Unicode)
    url_logo = db.Column(db.Unicode)
    id_parent = db.Column(db.Integer, db.ForeignKey("utilisateurs.bib_organismes.id_organisme"))
    additional_data = db.Column(JSONB, nullable=True, server_default="{}")
    members = db.relationship(User, backref="organisme")

    def __str__(self):
        return self.nom_organisme


profils_for_app = db.Table(
    "cor_profil_for_app",
    db.Column(
        "id_profil",
        db.Integer,
        ForeignKey("utilisateurs.t_profils.id_profil"),
        primary_key=True,
    ),
    db.Column(
        "id_application",
        db.Integer,
        ForeignKey("utilisateurs.t_applications.id_application"),
        primary_key=True,
    ),
    schema="utilisateurs",
)


class Profils(db.Model):
    """
    Model de la classe t_profils
    """

    __tablename__ = "t_profils"
    __table_args__ = {"schema": "utilisateurs", "extend_existing": True}
    id_profil = db.Column(db.Integer, primary_key=True)
    code_profil = db.Column(db.Unicode)
    nom_profil = db.Column(db.Unicode)
    desc_profil = db.Column(db.Unicode)

    applications = relationship("Application", secondary=profils_for_app, back_populates="profils")


@serializable
class Application(db.Model):
    """
    Représente une application ou un module
    """

    __tablename__ = "t_applications"
    __table_args__ = {"schema": "utilisateurs"}
    id_application = db.Column(db.Integer, primary_key=True)
    code_application = db.Column(db.Integer)
    nom_application = db.Column(db.Unicode)
    desc_application = db.Column(db.Unicode)
    id_parent = db.Column(db.Integer)

    profils = relationship(Profils, secondary=profils_for_app, back_populates="applications")

    def __repr__(self):
        return "<Application {!r}>".format(self.nom_application)

    def __str__(self):
        return self.nom_application

    @staticmethod
    def get_application(nom_application):
        return Application.query.filter(Application.nom_application == nom_application).one()


class ApplicationRight(db.Model):
    """
    Droit d'acces a une application
    """

    __tablename__ = "bib_droits"
    __table_args__ = {"schema": "utilisateurs"}
    id_droit = db.Column(db.Integer, primary_key=True)
    nom_droit = db.Column(db.Unicode)
    desc_droit = db.Column(db.UnicodeText)

    def __repr__(self):
        return "<ApplicationRight {!r}>".format(self.desc_droit)

    def __str__(self):
        return self.nom_droit


class UserApplicationRight(db.Model):
    """
    Droit d'acces d'un user particulier a une application particuliere
    """

    __tablename__ = "cor_role_app_profil"
    __table_args__ = {"schema": "utilisateurs"}  # , 'extend_existing': True}
    id_role = db.Column(db.Integer, ForeignKey("utilisateurs.t_roles.id_role"), primary_key=True)
    id_profil = db.Column(
        db.Integer, ForeignKey("utilisateurs.t_profils.id_profil"), primary_key=True
    )
    id_application = db.Column(
        db.Integer, ForeignKey("utilisateurs.t_applications.id_application"), primary_key=True
    )

    role = relationship("User")
    profil = relationship("Profils")
    application = relationship("Application")

    def __repr__(self):
        return "<UserApplicationRight role='{}' profil='{}' app='{}'>".format(
            self.id_role, self.id_profil, self.id_application
        )


@serializable(exclude=["password", "_password_plus"])
class AppUser(db.Model):
    """
    Relations entre applications et utilisateurs
    """

    __tablename__ = "v_userslist_forall_applications"
    __table_args__ = {"schema": "utilisateurs"}

    id_role = db.Column(
        db.Integer, db.ForeignKey("utilisateurs.t_roles.id_role"), primary_key=True
    )
    role = relationship("User", backref="app_users")
    nom_role = db.Column(db.Unicode)
    prenom_role = db.Column(db.Unicode)
    id_application = db.Column(
        db.Integer, db.ForeignKey("utilisateurs.t_applications.id_application"), primary_key=True
    )
    id_organisme = db.Column(db.Integer)
    application = relationship("Application", backref="app_users")
    identifiant = db.Column(db.Unicode)
    _password = db.Column("pass", db.Unicode)
    _password_plus = db.Column("pass_plus", db.Unicode)
    id_droit_max = db.Column(db.Integer, primary_key=True)
    # user = db.relationship('User', backref='relations', lazy='joined')
    # application = db.relationship('Application',
    #                               backref='relations', lazy='joined')

    @property
    def password(self):
        return self._password

    check_password = fn_check_password

    def __repr__(self):
        return "<AppUser role='{}' app='{}'>".format(self.id_role, self.id_application)


class AppRole(db.Model):
    """
    Relations entre applications et role
    """

    __tablename__ = "v_roleslist_forall_applications"
    __table_args__ = {"schema": "utilisateurs"}

    id_role = db.Column(
        db.Integer, db.ForeignKey("utilisateurs.t_roles.id_role"), primary_key=True
    )
    groupe = db.Column(db.Boolean)
    nom_role = db.Column(db.Unicode)
    prenom_role = db.Column(db.Unicode)
    id_application = db.Column(
        db.Integer, db.ForeignKey("utilisateurs.t_applications.id_application"), primary_key=True
    )
    id_organisme = db.Column(db.Integer)
    identifiant = db.Column(db.Unicode)

    application = db.relationship(Application)

    def as_dict(self):
        cols = (c for c in self.__table__.columns)
        return {c.name: getattr(self, c.name) for c in cols}


cor_role_liste = db.Table(
    "cor_role_liste",
    db.Column(
        "id_role",
        db.Integer,
        ForeignKey("utilisateurs.t_roles.id_role"),
        primary_key=True,
    ),
    db.Column(
        "id_liste",
        db.Integer,
        ForeignKey("utilisateurs.t_listes.id_liste"),
        primary_key=True,
    ),
    schema="utilisateurs",
)


@serializable
class UserList(db.Model):
    __tablename__ = "t_listes"
    __table_args__ = {"schema": "utilisateurs"}

    id_liste = db.Column(db.Integer, primary_key=True)
    code_liste = db.Column(db.Unicode(length=20))
    nom_liste = db.Column(db.Unicode(length=50))
    desc_liste = db.Column(db.Unicode)

    users = db.relationship(User, secondary=cor_role_liste)
