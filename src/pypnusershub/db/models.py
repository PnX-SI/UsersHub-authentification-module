# coding: utf8

from __future__ import (unicode_literals, print_function,
                        absolute_import, division)

'''
mappings applications et utilisateurs
'''

import hashlib

from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.orm import relationship, Sequence

db = SQLAlchemy()



class User(db.Model):

    __tablename__ = 't_roles'
    __table_args__ = {'schema': 'utilisateurs'}

    TABLE_ID = Sequence('t_roles_id_seq', start=1000)

    groupe = db.Column(db.Boolean)
    id_role = db.Column(
        db.Integer,
        TABLE_ID,
        primary_key=True,
        server_default=TABLE_ID.next_value()
    )
    # TODO: make that unique ?
    identifiant = db.Column(db.Unicode)
    nom_role = db.Column(db.Unicode)
    prenom_role = db.Column(db.Unicode)
    desc_role = db.Column(db.Unicode)
    _password = db.Column('pass', db.Unicode)
    email = db.Column(db.Unicode)
    id_organisme = db.Column(db.Integer)
    organisme = db.Column(db.Unicode)
    id_unite = db.Column(db.Integer)
    remarques = db.Column(db.Unicode)
    pn = db.Column(db.Boolean)
    session_appli = db.Column(db.Unicode)
    date_insert = db.Column(db.DateTime)
    date_update = db.Column(db.DateTime)

    # applications_droits = db.relationship('AppUser', lazy='joined')

    @property
    def password(self):
        return self._password

    # TODO: change password digest algorithm for something stronger such
    # as bcrypt. This need to be done at usershub level first.
    @password.setter
    def password(self, pwd):
        self._password = hashlib.md5(pwd.encode('utf8')).hexdigest()

    def check_password(self, pwd):
        return self._password == hashlib.md5(pwd.encode('utf8')).hexdigest()

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
        return self.identifiant


class Application(db.Model):
    '''
    Représente une application ou un module
    '''
    __tablename__ = 't_applications'
    __table_args__ = {'schema': 'utilisateurs'}
    id_application = db.Column(db.Integer, primary_key=True)
    nom_application = db.Column(db.Unicode)
    desc_application = db.Column(db.Unicode)

    def __repr__(self):
        return "<Application {!r}>".format(self.nom_application)

    def __str__(self):
        return self.nom_application


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
    __tablename__ = 'cor_role_droit_application'
    __table_args__ = {'schema': 'utilisateurs'}
    id_role = db.Column(db.Integer, primary_key=True)
    id_droit = db.Column(db.Integer, primary_key=True)
    id_application = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return "<UserApplicationRight role='{}' droit='{}' app='{}'>".format(
            self.id_role, self.id_droit, self.id_application
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
    id_application = db.Column(
        db.Integer,
        db.ForeignKey('utilisateurs.t_applications.id_application'),
        primary_key=True
    )
    application = relationship("Application", backref="app_users")
    identifiant = db.Column(db.Unicode)
    _password = db.Column('pass', db.Unicode)
    id_droit_max = db.Column(db.Integer, primary_key=True)
    # user = db.relationship('User', backref='relations', lazy='joined')
    # application = db.relationship('Application',
    #                               backref='relations', lazy='joined')

    @property
    def password(self):
        return self._password

    def check_password(self, pwd):
        return self._password == hashlib.md5(pwd.encode('utf8')).hexdigest()

    def as_dict(self):
        cols = (c for c in self.__table__.columns if c.name != 'pass')
        return {c.name: getattr(self, c.name) for c in cols}

    def __repr__(self):
        return "<AppUser role='{}' app='{}'>".format(
            self.id_role, self.id_application
        )
