# coding: utf8

from __future__ import absolute_import, division, print_function, unicode_literals

import secrets
import hashlib
import uuid
from typing import Optional, List
from datetime import datetime

import re

import bcrypt
from bcrypt import checkpw
import flask_sqlalchemy
from packaging import version

from flask import current_app
from flask_login import UserMixin

from sqlalchemy import ForeignKey, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB, UUID, array
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column, object_session, Session
from sqlalchemy.schema import FetchedValue

from pypnusershub.db.tools import DifferentPasswordError, NoPasswordError
from pypnusershub.env import db
from pypnusershub.utils import get_current_app_id

from utils_flask_sqla.serializers import serializable

# Compatibility for Flask-SQLAlchemy Query import (kept for potential compatibility)
if version.parse(flask_sqlalchemy.__version__) >= version.parse("3"):
    from flask_sqlalchemy.query import Query  # noqa: F401
else:
    from flask_sqlalchemy import BaseQuery as Query  # noqa: F401


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


# association tables (we keep db.Table to remain compatible with Flask-SQLAlchemy)
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


class CorRoles(db.Model):
    __table__ = cor_roles


cor_role_provider = db.Table(
    "cor_role_provider",
    db.Column(
        "id_role",
        db.Integer,
        ForeignKey("utilisateurs.t_roles.id_role"),
        primary_key=True,
    ),
    db.Column(
        "id_provider",
        db.Integer,
        ForeignKey("utilisateurs.t_providers.id_provider"),
        primary_key=True,
    ),
    schema="utilisateurs",
)

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


# --- Models ---


class PasswordMixin:
    def check_password(self, pwd):
        if self._password_plus:
            return checkpw(pwd.encode("utf8"), self._password_plus.encode("utf8"))
        elif self._password:
            are_passwords_equal = (
                self._password == hashlib.md5(pwd.encode("utf8")).hexdigest()
            )
            if are_passwords_equal:
                self.password = pwd  # This will hash the password with bcrypt and update _password_plus
                db.session.commit()
            return are_passwords_equal
        else:
            raise ValueError(f"User {self.identifiant} has no password")


@serializable(
    exclude=["_password", "password", "_password_plus", "api_key", "api_secret"]
)
class User(db.Model, UserMixin, PasswordMixin):
    __tablename__ = "t_roles"
    __table_args__ = {"schema": "utilisateurs"}

    # modern mapped columns
    id_role: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    uuid_role: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), server_default=FetchedValue()
    )
    groupe: Mapped[bool] = mapped_column(db.Boolean, default=False)

    identifiant: Mapped[Optional[str]] = mapped_column(db.Unicode)
    nom_role: Mapped[Optional[str]] = mapped_column(db.Unicode)
    prenom_role: Mapped[Optional[str]] = mapped_column(db.Unicode)
    desc_role: Mapped[Optional[str]] = mapped_column(db.Unicode)

    _password: Mapped[Optional[str]] = mapped_column("pass", db.Unicode)
    _password_plus: Mapped[Optional[str]] = mapped_column("pass_plus", db.Unicode)

    email: Mapped[Optional[str]] = mapped_column(db.Unicode)
    id_organisme: Mapped[Optional[int]] = mapped_column(
        db.Integer, ForeignKey("utilisateurs.bib_organismes.id_organisme")
    )
    # back_populates set on Organisme.members
    organisme: Mapped[Optional["Organisme"]] = relationship(
        "Organisme", back_populates="members"
    )

    remarques: Mapped[Optional[str]] = mapped_column(db.Unicode)
    champs_addi: Mapped[Optional[dict]] = mapped_column(JSONB)
    date_insert: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    date_update: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    active: Mapped[Optional[bool]] = mapped_column(db.Boolean)
    api_key: Mapped[Optional[str]] = mapped_column(db.Unicode)
    api_secret: Mapped[Optional[str]] = mapped_column(db.Unicode)

    # associations (groups <-> members via cor_roles)
    groups: Mapped[List["User"]] = relationship(
        "User",
        secondary=cor_roles,
        primaryjoin="User.id_role==utilisateurs.cor_roles.c.id_role_utilisateur",
        secondaryjoin="User.id_role==utilisateurs.cor_roles.c.id_role_groupe",
        back_populates="members",
        viewonly=False,
    )

    members: Mapped[List["User"]] = relationship(
        "User",
        secondary=cor_roles,
        primaryjoin="User.id_role==utilisateurs.cor_roles.c.id_role_groupe",
        secondaryjoin="User.id_role==utilisateurs.cor_roles.c.id_role_utilisateur",
        back_populates="groups",
        viewonly=False,
    )

    providers: Mapped[List["Provider"]] = relationship(
        "Provider", secondary=cor_role_provider, back_populates="users"
    )

    # ---------------------
    # Méthodes / propriétés
    # ---------------------

    @property
    def max_level_profil(self):
        """
        Retourne le niveau maximal de profil pour cet utilisateur dans l'application courante.
        Utilise la session de l'instance via object_session(self).
        """
        sess = object_session(self)
        group_ids = [role.id_role for role in (self.groups or [])]
        stmt = (
            select(func.max(Profils.code_profil))
            .select_from(User)
            .join(
                UserApplicationRight,
                or_(
                    UserApplicationRight.id_role == self.id_role,
                    UserApplicationRight.id_role.in_(group_ids),
                ),
            )
            .join(Profils, UserApplicationRight.id_profil == Profils.id_profil)
            .where(UserApplicationRight.id_application == get_current_app_id())
        )
        res = sess.execute(stmt).scalar_one_or_none()
        return res or 0

    @hybrid_property
    def nom_complet(self):
        return " ".join([i for i in [self.nom_role, self.prenom_role] if i])

    @nom_complet.expression
    def nom_complet(cls):
        return func.array_to_string(array([cls.nom_role, cls.prenom_role]), " ")

    def get_id(self):
        return str(self.id_role)

    @property
    def password(self):
        return self._password_plus or self._password

    @password.setter
    def password(self, password):
        """
        Set the user's password, hashing it with bcrypt (auto-salted) and storing the hash.

        Parameters
        ----------
        password : str
            The plaintext password to set for the user.

        """
        self._password_plus = bcrypt.hashpw(
            password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def generate_api_secret(self):
        """
        Generate a secure random API secret, hash it with bcrypt (auto-salted), and store the hash.
        If Api secret already exists replace it.

        Returns
        -------
        tuple
            The API key and the raw API secret.
        """
        raw_key = secrets.token_hex(128)
        hashed_key = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt())
        self.api_secret = hashed_key.decode("utf-8")
        # keep uuid_role as api_key if present, else None
        self.api_key = str(self.uuid_role) if self.uuid_role else None
        db.session.commit()
        return self.api_key, raw_key

    @staticmethod
    def check_api_key(key: str, secret: str):
        """
        Check if the couple api_key and api_secret match.

        Parameters
        ----------
        key : str
            The API key to check.
        secret : str
            The API secret to check.

        Returns
        -------
        User or None
            The user corresponding to the API key and secret if they match, None otherwise.
        """
        stmt = select(User).where(User.api_key == key)
        user = db.session.execute(stmt).scalars().one_or_none()
        if not user or not user.api_secret:
            return None
        if bcrypt.checkpw(secret.encode(), user.api_secret.encode()):
            return user
        return None

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

    # --- New SQLAlchemy 2.0 style utility: classmethod replacing old qfilter/UserQuery ---
    @classmethod
    def filter_by_app(cls, code_app: Optional[int] = None, **kwargs):
        """
        Retourne une expression booléenne utilisable dans .where() pour filtrer
        les Users visibles par l'application `code_app`.
        Usage:
            stmt = select(User).where(User.filter_by_app(code_app))
            users = session.scalars(stmt).all()
        Si code_app est None, prends current_app.config['CODE_APPLICATION'].
        """
        if code_app is None:
            code_app = current_app.config.get("CODE_APPLICATION")
        subq = (
            select(cls.id_role)
            .outerjoin(cor_roles, cls.id_role == cor_roles.c.id_role_utilisateur)
            .outerjoin(
                UserApplicationRight,
                or_(
                    UserApplicationRight.id_role == cor_roles.c.id_role_groupe,
                    UserApplicationRight.id_role == cls.id_role,
                ),
            )
            .join(
                Application,
                Application.id_application == UserApplicationRight.id_application,
            )
            .where(Application.code_application == code_app)
        )
        return cls.id_role.in_(subq)


@serializable
class Organisme(db.Model):
    __tablename__ = "bib_organismes"
    __table_args__ = {"schema": "utilisateurs"}

    id_organisme: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    uuid_organisme: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), server_default=FetchedValue()
    )
    nom_organisme: Mapped[str] = mapped_column(db.Unicode)
    adresse_organisme: Mapped[Optional[str]] = mapped_column(db.Unicode)
    cp_organisme: Mapped[Optional[str]] = mapped_column(db.Unicode)
    ville_organisme: Mapped[Optional[str]] = mapped_column(db.Unicode)
    tel_organisme: Mapped[Optional[str]] = mapped_column(db.Unicode)
    fax_organisme: Mapped[Optional[str]] = mapped_column(db.Unicode)
    email_organisme: Mapped[Optional[str]] = mapped_column(db.Unicode)
    url_organisme: Mapped[Optional[str]] = mapped_column(db.Unicode)
    url_logo: Mapped[Optional[str]] = mapped_column(db.Unicode)
    id_parent: Mapped[Optional[int]] = mapped_column(
        db.Integer, db.ForeignKey("utilisateurs.bib_organismes.id_organisme")
    )
    additional_data: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, server_default="{}"
    )
    meta_create_date: Mapped[Optional[datetime]] = mapped_column(db.DateTime)
    meta_update_date: Mapped[Optional[datetime]] = mapped_column(db.DateTime)

    members: Mapped[List[User]] = relationship("User", back_populates="organisme")

    def __str__(self):
        return self.nom_organisme


class Profils(db.Model):
    __tablename__ = "t_profils"
    __table_args__ = {"schema": "utilisateurs", "extend_existing": True}

    id_profil: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    code_profil: Mapped[Optional[int]]
    nom_profil: Mapped[Optional[str]]
    desc_profil: Mapped[Optional[str]]

    applications: Mapped[List["Application"]] = relationship(
        "Application", secondary=profils_for_app, back_populates="profils"
    )


@serializable
class Application(db.Model):
    __tablename__ = "t_applications"
    __table_args__ = {"schema": "utilisateurs"}

    id_application: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    code_application: Mapped[str] = mapped_column(db.Unicode)
    nom_application: Mapped[str] = mapped_column(db.Unicode)
    desc_application: Mapped[Optional[str]] = mapped_column(db.Unicode)
    id_parent: Mapped[Optional[int]] = mapped_column(db.Integer)

    profils: Mapped[List[Profils]] = relationship(
        Profils, secondary=profils_for_app, back_populates="applications"
    )

    def __repr__(self):
        return "<Application {!r}>".format(self.nom_application)

    def __str__(self):
        return self.nom_application

    @staticmethod
    def get_application(nom_application: str) -> "Application":
        return db.session.execute(
            select(Application).where(Application.nom_application == nom_application)
        ).scalar_one()


class UserApplicationRight(db.Model):
    __tablename__ = "cor_role_app_profil"
    __table_args__ = {"schema": "utilisateurs"}

    id_role: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("utilisateurs.t_roles.id_role"), primary_key=True
    )
    id_profil: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("utilisateurs.t_profils.id_profil"), primary_key=True
    )
    id_application: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("utilisateurs.t_applications.id_application"),
        primary_key=True,
    )
    is_default_group_for_app = db.Column(db.Boolean, default=False)

    role: Mapped[Optional[User]] = relationship("User")
    profil: Mapped[Optional[Profils]] = relationship("Profils")
    application: Mapped[Optional[Application]] = relationship("Application")

    def __repr__(self):
        return "<UserApplicationRight role='{}' profil='{}' app='{}'>".format(
            self.id_role, self.id_profil, self.id_application
        )

    @staticmethod
    def get_default_for_app(id_application):
        return (
            db.session.query(UserApplicationRight)
            .filter_by(id_application=id_application)
            .filter_by(is_default_group_for_app=True)
            .first()
        )


@serializable(exclude=["password", "_password_plus"])
class AppUser(db.Model):
    __tablename__ = "v_userslist_forall_applications"
    __table_args__ = {"schema": "utilisateurs"}

    id_role: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("utilisateurs.t_roles.id_role"), primary_key=True
    )
    role: Mapped[Optional[User]] = relationship("User", backref="app_users")
    nom_role: Mapped[Optional[str]] = mapped_column(db.Unicode)
    prenom_role: Mapped[Optional[str]] = mapped_column(db.Unicode)
    id_application: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("utilisateurs.t_applications.id_application"),
        primary_key=True,
    )
    id_organisme: Mapped[Optional[int]] = mapped_column(db.Integer)
    application: Mapped[Optional[Application]] = relationship(
        "Application", backref="app_users"
    )
    identifiant: Mapped[Optional[str]] = mapped_column(db.Unicode)
    _password: Mapped[Optional[str]] = mapped_column("pass", db.Unicode)
    _password_plus: Mapped[Optional[str]] = mapped_column("pass_plus", db.Unicode)
    id_droit_max: Mapped[Optional[int]] = mapped_column(db.Integer, primary_key=True)

    @property
    def password(self):
        return self._password

    def __repr__(self):
        return "<AppUser role='{}' app='{}'>".format(self.id_role, self.id_application)


class AppRole(db.Model):
    __tablename__ = "v_roleslist_forall_applications"
    __table_args__ = {"schema": "utilisateurs"}

    id_role: Mapped[int] = mapped_column(
        db.Integer, ForeignKey("utilisateurs.t_roles.id_role"), primary_key=True
    )
    groupe: Mapped[Optional[bool]] = mapped_column(db.Boolean)
    nom_role: Mapped[Optional[str]] = mapped_column(db.Unicode)
    prenom_role: Mapped[Optional[str]] = mapped_column(db.Unicode)
    id_application: Mapped[int] = mapped_column(
        db.Integer,
        ForeignKey("utilisateurs.t_applications.id_application"),
        primary_key=True,
    )
    id_organisme: Mapped[Optional[int]] = mapped_column(db.Integer)
    identifiant: Mapped[Optional[str]] = mapped_column(db.Unicode)

    application: Mapped[Optional[Application]] = relationship("Application")

    def as_dict(self):
        cols = (c for c in self.__table__.columns)
        return {c.name: getattr(self, c.name) for c in cols}


@serializable
class UserList(db.Model):
    __tablename__ = "t_listes"
    __table_args__ = {"schema": "utilisateurs"}

    id_liste: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    code_liste: Mapped[str] = mapped_column(db.Unicode(length=20))
    nom_liste: Mapped[str] = mapped_column(db.Unicode(length=50))
    desc_liste: Mapped[Optional[str]] = mapped_column(db.Unicode)

    users: Mapped[List[User]] = relationship("User", secondary=cor_role_liste)


@serializable
class Provider(db.Model):
    __tablename__ = "t_providers"
    __table_args__ = {"schema": "utilisateurs"}

    id_provider: Mapped[int] = mapped_column(
        db.Integer, nullable=False, primary_key=True
    )
    name: Mapped[str] = mapped_column(db.Unicode, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(db.Unicode)

    users: Mapped[List[User]] = relationship(
        "User", secondary=cor_role_provider, back_populates="providers"
    )


class CorRoleToken(db.Model):
    __tablename__ = "cor_role_token"
    __table_args__ = {"schema": "utilisateurs", "extend_existing": True}

    id_role: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[Optional[str]]

    def as_dict(self, recursif=False, columns=(), depth=None):
        """
        The signature of the function must be the as same the as_dict func
        from https://github.com/PnX-SI/Utils-Flask-SQLAlchemy
        """
        return {"id_role": self.id_role, "token": self.token}


@serializable
class CorRoleListe(db.Model):
    """Classe de correspondance entre la table t_roles et la table t_listes"""

    __table__ = cor_role_liste


class TempUser(db.Model):
    __tablename__ = "temp_users"
    __table_args__ = {"schema": "utilisateurs", "extend_existing": True}

    id_temp_user: Mapped[int] = mapped_column(primary_key=True)
    token_role: Mapped[Optional[str]]
    organisme: Mapped[Optional[str]]
    id_application: Mapped[int]
    confirmation_url: Mapped[Optional[str]]
    groupe: Mapped[bool]
    identifiant: Mapped[Optional[str]]
    nom_role: Mapped[Optional[str]]
    prenom_role: Mapped[Optional[str]]
    desc_role: Mapped[Optional[str]]
    password: Mapped[Optional[str]]
    pass_md5: Mapped[Optional[str]]
    email: Mapped[Optional[str]]
    id_organisme: Mapped[Optional[int]]
    remarques: Mapped[Optional[str]]
    champs_addi: Mapped[Optional[dict]] = mapped_column(JSONB)
    date_insert: Mapped[Optional[datetime]]
    date_update: Mapped[Optional[datetime]]

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
        role = db.session.scalars(
            select(User).where(
                or_(User.email == self.email, User.identifiant == self.identifiant)
            )
        ).first()
        if role:
            is_valid = False
            if role.email == self.email:
                msg += (
                    f"Un compte avec l'email {self.email} existe déjà. "
                    + "S'il s'agit de votre email, vous pouvez faire une demande de renouvellement "
                    + "de mot de passe via la page de login de GeoNature."
                )
            else:
                msg += (
                    f"Un compte avec l'identifiant {self.identifiant} existe déjà. "
                    + "Veuillez choisir un identifiant différent."
                )

        temp_role = db.session.scalars(
            select(TempUser)
            .where(
                or_(
                    TempUser.email == self.email,
                    TempUser.identifiant == self.identifiant,
                )
            )
            .limit(1)
        ).first()
        if temp_role:
            is_valid = False
            if temp_role.email == self.email:
                msg += (
                    f"Un compte en attente de validation avec l'email {self.email} existe déjà. "
                    + "Merci de patienter le temps que votre demande soit traitée."
                )
            else:
                msg += (
                    "Un compte en attente de validation avec l'identifiant "
                    + f"{self.identifiant} existe déjà. "
                    + "Veuillez choisir un identifiant différent."
                )

        return (is_valid, msg)

    def as_dict(self, recursif=False, columns=(), depth=None):
        """
        The signature of the function must be the as same the as_dict func
        from https://github.com/PnX-SI/Utils-Flask-SQLAlchemy
        """
        return {
            "id_temp_user": self.id_temp_user,
            "token_role": self.token_role,
            "organisme": self.organisme,
            "id_application": self.id_application,
            "confirmation_url": self.confirmation_url,
            "groupe": self.groupe,
            "identifiant": self.identifiant,
            "nom_role": self.nom_role,
            "prenom_role": self.prenom_role,
            "desc_role": self.desc_role,
            "password": self.password,
            "pass_md5": self.pass_md5,
            "email": self.email,
            "id_organisme": self.id_organisme,
            "remarques": self.remarques,
            "champs_addi": self.champs_addi,
        }
