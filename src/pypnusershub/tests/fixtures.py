import pytest
from pypnusershub.env import db
from pypnusershub.db.models import Organisme, Application, User, Profils, UserApplicationRight

organism = {
    "nom_organisme": "test",
    "id_organisme": 99999,
    "adresse_organisme": "66 rue du truc",
    "ville_organisme": "Gap",
    "tel_organisme": "00000000",
    "email_organisme": "test@test.com",
    "url_organisme": "http://lala.com",
    "url_logo": "http://lala.com",
    "url_logo": "http://lala.com",
}


@pytest.fixture(scope="function")
def organism(app):
    with db.session.begin_nested():
        org = Organisme(nom_organisme="test")
        db.session.add(org)
    return org


@pytest.fixture(scope="function")
def profil(app):
    with db.session.begin_nested():
        profil = Profils(code_profil="ADMIN", nom_profil="Admin")
        db.session.add(profil)
    return profil


@pytest.fixture(scope="function")
def applications(app):
    with db.session.begin_nested():
        app1 = Application(code_application="APPLI_1", nom_application="application 1")
        app2 = Application(code_application="APPLI_2", nom_application="application 2")
        db.session.add(app1)
        db.session.add(app2)
    return {
        "app1": app1,
        "app2": app2,
    }


@pytest.fixture(scope="function")
def group_and_users(app, applications, profil):
    with db.session.begin_nested():
        group1 = User(groupe=True, identifiant="group1")
        db.session.add(group1)
        user1 = User(groupe=False, identifiant="user_of_group1")
        user2 = User(groupe=True, identifiant="user2")
        user1.groups.append(group1)
        db.session.add(user1)
        db.session.add(user2)
        db.session.flush()
        user_app = UserApplicationRight(
            id_role=group1.id_role,
            id_profil=profil.id_profil,
            id_application=applications["app1"].id_application,
        )
        db.session.add(user_app)
        return {
            "group1": group1,
            "user1": user1,
            "user2": user2,
        }
