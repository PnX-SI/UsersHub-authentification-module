#coding: utf8

'''
mappings applications et utilisateurs
'''

import hashlib
from server import db


class User(db.Model):
    '''
    Représente un utilisateur
    '''
    __tablename__ = 'utilisateur'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.Unicode)
    _password = db.Column('password', db.Unicode)
    email = db.Column(db.Unicode)
    token = db.Column(db.Unicode)
    applications = db.relationship('AppUser', lazy='joined')

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, pwd):
        self._password = hashlib.sha256(pwd.encode('utf8')).hexdigest() 

    def check_password(self, pwd):
        print(pwd)
        return self._password == hashlib.sha256(pwd.encode('utf8')).hexdigest() 

    def to_json(self):
        out = {
                'id': self.id,
                'login': self.login,
                'email': self.email,
                'applications': []
                }
        for app_data in self.applications:
            app = {
                    'id': app_data.application_id,
                    'nom': app_data.application.nom,
                    'niveau': app_data.niveau
                    }
            out['applications'].append(app)
        return out




class Application(db.Model):
    '''
    Représente une application ou un module
    '''
    __tablename__ = 'application'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.Unicode)




class AppUser(db.Model):
    '''
    Relations entre applications et utilisateurs
    '''
    __tablename__ = 'rel_app_user'
    user_id = db.Column(db.Integer, 
            db.ForeignKey('utilisateur.id'), primary_key=True)
    application_id = db.Column(db.Integer,
            db.ForeignKey('application.id'), primary_key=True)
    niveau = db.Column(db.Integer)
    user = db.relationship('User', 
            backref='relations', lazy='joined')
    application = db.relationship('Application', 
            backref='relations', lazy='joined')
    
