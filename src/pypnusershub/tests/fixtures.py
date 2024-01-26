import pytest

from flask_login import logout_user
from pypnusershub.env import db
from pypnusershub.db.models import (
    Organisme,
    Application,
    User,
    Profils,
    UserApplicationRight,
)

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


@pytest.fixture(autouse=True)
def teardown_logout_user():
    yield
    logout_user()


@pytest.fixture(scope="function")
def organism(app):
    with db.session.begin_nested():
        org = Organisme(nom_organisme="test")
        db.session.add(org)
    return org


@pytest.fixture(scope="function")
def profils(app):
    with db.session.begin_nested():
        profil_high = Profils(code_profil=6, nom_profil="Admin")
        profil_low = Profils(code_profil=1, nom_profil="Lecteur")
        db.session.add(profil_high)
        db.session.add(profil_low)
    return {"admin": profil_high, "reader": profil_low}


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
def group_and_users(app, applications, profils):
    with db.session.begin_nested():
        group1 = User(groupe=True, identifiant="group1")
        db.session.add(group1)
        user1 = User(groupe=False, identifiant="user_of_group1")
        user1.password = "admin"
        user_no_group = User(groupe=False, identifiant="user2")
        user1.groups.append(group1)
        db.session.add(user1)
        db.session.add(user_no_group)
        db.session.flush()
        group_app = UserApplicationRight(
            id_role=group1.id_role,
            id_profil=profils["admin"].id_profil,
            id_application=applications["app1"].id_application,
        )
        user_app = UserApplicationRight(
            id_role=user1.id_role,
            id_profil=profils["reader"].id_profil,
            id_application=applications["app1"].id_application,
        )
        user_no_group_app = UserApplicationRight(
            id_role=user_no_group.id_role,
            id_profil=profils["reader"].id_profil,
            id_application=applications["app1"].id_application,
        )
        db.session.add(group_app)
        db.session.add(user_app)
        db.session.add(user_no_group_app)
        return {
            "group1": group1,
            "user1": user1,
            "user_no_group": user_no_group,
        }
