# coding: utf8

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)

'''
mappings applications et utilisateurs
'''

import hashlib
import bcrypt
from bcrypt import checkpw

from flask_sqlalchemy import SQLAlchemy

from flask import current_app

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy import Sequence, func, ForeignKey

from pypnusershub.db.tools import NoPasswordError, DifferentPasswordError
db = current_app.config['DB']


def check_and_encrypt_password(password, password_confirmation, md5=False):
    if not password:
        raise NoPasswordError
    if password != password_confirmation:
        raise DifferentPasswordError
    try:
        pass_plus = bcrypt.hashpw(password.encode(
            'utf-8'), bcrypt.gensalt())
        pass_md5 = None
        if md5:
            pass_md5 = hashlib.md5(password.encode("utf-8")).hexdigest()
    except Exception as e:
        raise e
    return pass_plus.decode('utf-8'), pass_md5


def fn_check_password(self, pwd):
    if (current_app.config['PASS_METHOD'] == 'md5'):
        if not self._password:
            raise ValueError('User %s has no password' % (self.identifiant))
        return self._password == hashlib.md5(pwd.encode('utf8')).hexdigest()
    elif (current_app.config['PASS_METHOD'] == 'hash'):
        if not self._password_plus:
            raise ValueError('User %s has no password' % (self.identifiant))
        return checkpw(pwd.encode('utf8'), self._password_plus.encode('utf8'))
    else:
        raise ValueError('Undefine crypt method (PASS_METHOD)')


class User(db.Model):
    __tablename__ = 't_roles'
    __table_args__ = {'schema': 'utilisateurs'}

    TABLE_ID = Sequence(
        't_roles_id_seq',
        schema="utilisateurs",
    )
    groupe = db.Column(db.Boolean, default=False)
    id_role = db.Column(
        db.Integer,
        TABLE_ID,
        primary_key=True,
    )

    # TODO: make that unique ?
    identifiant = db.Column(db.Unicode)
    nom_role = db.Column(db.Unicode)
    prenom_role = db.Column(db.Unicode)
    desc_role = db.Column(db.Unicode)
    _password = db.Column('pass', db.Unicode)
    _password_plus = db.Column('pass_plus', db.Unicode)
    email = db.Column(db.Unicode)
    id_organisme = db.Column(db.Integer)
    remarques = db.Column(db.Unicode)
    date_insert = db.Column(db.DateTime)
    date_update = db.Column(db.DateTime)
    active = db.Column(db.Boolean)

    @hybrid_property
    def nom_complet(self):
        return '{0} {1}'.format(self.nom_role, self.prenom_role)

    @nom_complet.expression
    def nom_complet(cls):
        return db.func.concat(cls.nom_role, ' ', cls.prenom_role)

    # applications_droits = db.relationship('AppUser', lazy='joined')

    @property
    def password(self):
        if (current_app.config['PASS_METHOD'] == 'md5'):
            return self._password
        elif (current_app.config['PASS_METHOD'] == 'hash'):
            return self._password_plus
        else:
            raise

    # TODO: change password digest algorithm for something stronger such
    # as bcrypt. This need to be done at usershub level first.
    @password.setter
    def password(self, pwd):
        self._password = hashlib.md5(pwd.encode('utf8')).hexdigest()

    check_password = fn_check_password

    def to_json(self):
        out = {
            'id': self.id_role,
            'login': self.identifiant,
            'email': self.email,
            'applications': []
        }
        for app_data in self.applications_droits:
            app = {
                'id': app_data.application_id,
                'nom': app_data.application.nom_application,
                'niveau': app_data.id_droit_max
            }
            out['applications'].append(app)
        return out

    def __repr__(self):
        return "<User '{!r}' id='{}'>".format(self.identifiant, self.id_role)

    def __str__(self):
        return self.identifiant or ''

    def as_dict(self, recursif=False, columns=(), relationships=(), depth=None):
        '''
            The signature of the function must be the as same the as_dict func from https://github.com/PnX-SI/Utils-Flask-SQLAlchemy
        '''
        nom_role = self.nom_role or ''
        prenom_role = self.prenom_role or ''
        return {
            'id_role': self.id_role,
            'identifiant': self.identifiant,
            'nom_role': self.nom_role,
            'prenom_role': self.prenom_role,
            'id_organisme': self.id_organisme,
            'email': self.email,
            'groupe': self.groupe,
            'remarques': self.remarques,
            'nom_complet': self.nom_complet
        }


class Profils(db.Model):
    """
    Model de la classe t_profils
    """

    __tablename__ = 't_profils'
    __table_args__ = {'schema': 'utilisateurs', 'extend_existing': True}
    id_profil = db.Column(db.Integer, primary_key=True)
    code_profil = db.Column(db.Unicode)
    nom_profil = db.Column(db.Unicode)
    desc_profil = db.Column(db.Unicode)


class ProfilsForApp(db.Model):
    """
    Model de la classe t_profils
    """

    __tablename__ = 'cor_profil_for_app'
    __table_args__ = {'schema': 'utilisateurs', 'extend_existing': True}
    id_profil = db.Column(
        db.Integer,
        ForeignKey('utilisateurs.t_profils.id_profil'),
        primary_key=True
    )
    id_application = db.Column(db.Integer, primary_key=True)

    profil = relationship("Profils")


class Application(db.Model):
    '''
    Représente une application ou un module
    '''
    __tablename__ = 't_applications'
    __table_args__ = {'schema': 'utilisateurs'}
    id_application = db.Column(db.Integer, primary_key=True)
    code_application = db.Column(db.Unicode)
    nom_application = db.Column(db.Unicode)
    desc_application = db.Column(db.Unicode)
    id_parent = db.Column(db.Integer)

    def __repr__(self):
        return "<Application {!r}>".format(self.nom_application)

    def __str__(self):
        return self.nom_application

    @staticmethod
    def get_application(nom_application):
        return (Application.query
                .filter(Application.nom_application == nom_application)
                .one())


class ApplicationRight(db.Model):
    '''
    Droit d'acces a une application
    '''
    __tablename__ = 'bib_droits'
    __table_args__ = {'schema': 'utilisateurs'}
    id_droit = db.Column(db.Integer, primary_key=True)
    nom_droit = db.Column(db.Unicode)
    desc_droit = db.Column(db.UnicodeText)

    def __repr__(self):
        return "<ApplicationRight {!r}>".format(self.desc_droit)

    def __str__(self):
        return self.nom_droit


class UserApplicationRight(db.Model):
    '''
    Droit d'acces d'un user particulier a une application particuliere
    '''
    __tablename__ = 'cor_role_app_profil'
    __table_args__ = {'schema': 'utilisateurs', 'extend_existing': True}
    id_role = db.Column(db.Integer, primary_key=True)
    id_profil = db.Column(db.Integer, ForeignKey(
        'utilisateurs.t_profils.id_profil'), primary_key=True)
    id_application = db.Column(db.Integer, primary_key=True)

    profil = relationship("Profils")

    def __repr__(self):
        return "<UserApplicationRight role='{}' profil='{}' app='{}'>".format(
            self.id_role, self.id_profil, self.id_application
        )


class AppUser(db.Model):
    '''
    Relations entre applications et utilisateurs
    '''
    __tablename__ = 'v_userslist_forall_applications'
    __table_args__ = {'schema': 'utilisateurs'}

    id_role = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.t_roles.id_role'),
        primary_key=True
    )
    role = relationship("User", backref="app_users")
    nom_role = db.Column(db.Unicode)
    prenom_role = db.Column(db.Unicode)
    id_application = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.t_applications.id_application'),
        primary_key=True
    )
    id_organisme = db.Column(db.Integer)
    application = relationship("Application", backref="app_users")
    identifiant = db.Column(db.Unicode)
    _password = db.Column('pass', db.Unicode)
    _password_plus = db.Column('pass_plus', db.Unicode)
    id_droit_max = db.Column(db.Integer, primary_key=True)
    # user = db.relationship('User', backref='relations', lazy='joined')
    # application = db.relationship('Application',
    #                               backref='relations', lazy='joined')

    @property
    def password(self):
        return self._password

    check_password = fn_check_password

    def as_dict(self):
        cols = (c for c in self.__table__.columns if (
            c.name != 'pass_plus') and (c.name != 'pass'))
        return {c.name: getattr(self, c.name) for c in cols}

    def __repr__(self):
        return "<AppUser role='{}' app='{}'>".format(
            self.id_role, self.id_application
        )


class AppRole(db.Model):
    '''
    Relations entre applications et role
    '''
    __tablename__ = 'v_roleslist_forall_applications'
    __table_args__ = {'schema': 'utilisateurs'}

    id_role = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.t_roles.id_role'),
        primary_key=True
    )
    groupe = db.Column(db.Boolean)
    nom_role = db.Column(db.Unicode)
    prenom_role = db.Column(db.Unicode)
    id_application = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.t_applications.id_application'),
        primary_key=True
    )
    id_organisme = db.Column(db.Integer)
    identifiant = db.Column(db.Unicode)

    def as_dict(self):
        cols = (c for c in self.__table__.columns)
        return {c.name: getattr(self, c.name) for c in cols}
