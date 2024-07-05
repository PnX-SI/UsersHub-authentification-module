from datetime import datetime
from flask import url_for

import pytest

from pypnusershub.db.models import Organisme, User

from pypnusershub.routes import insert_or_update_organism, insert_or_update_role
from pypnusershub.schemas import OrganismeSchema, UserSchema
from pypnusershub.tests.fixtures import *

from sqlalchemy import select

from pypnusershub.auth.auth_manager import auth_manager


@pytest.fixture
def provider_instance():
    return auth_manager.get_provider("local_provider")


@pytest.mark.usefixtures("client_class", "temporary_transaction")
class TestUtilisateurs:
    def test_insert_user(self, app, organism, group_and_users, provider_instance):
        user_schema = UserSchema(exclude=["nom_complet", "max_level_profil"])
        group = group_and_users["group1"]

        user_dict = {
            "id_role": 99999,
            "identifiant": "test.user",
            "nom_role": "test",
            "prenom_role": "test",
            "id_organisme": organism.id_organisme,
            "email": "test@test.fr",
            "active": True,
            "groups": [group],
        }
        user_ = User(**user_dict)
        user_ = insert_or_update_role(user_, provider_instance)
        user_.identifiant = "update"
        db.session.commit()

        created_user = db.session.get(User, 99999)
        user_schema = UserSchema(only=["groups"])
        created_user_as_dict = user_schema.dump(created_user)
        assert created_user_as_dict["identifiant"] == "update"
        assert created_user_as_dict["id_role"] == 99999
        assert len(created_user_as_dict["groups"]) == 1

        app.config["AUTHENTICATION"]["DEFAULT_RECONCILIATION_GROUP_ID"] = 2
        user_dict["id_role"] = 99998
        user_dict["email"] = "test@test2.fr"
        user_ = User(**user_dict)
        user_ = insert_or_update_role(user_, provider_instance)
        assert len(user_.groups) == 2

    def test_insert_organisme(self):
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
        insert_or_update_organism(organism)
        organism["nom_organisme"] = "update"
        insert_or_update_organism(organism)

        create_organism = db.session.get(Organisme, 99999)
        organism_schema = OrganismeSchema()
        organism_as_dict = organism_schema.dump(create_organism)
        assert organism_as_dict["nom_organisme"] == "update"

    def test_filter_by_app(self, group_and_users):
        roles = db.session.scalars(
            select(User).where(User.filter_by_app("APPLI_1"))
        ).all()
        assert set([group_and_users["group1"], group_and_users["user1"]]).issubset(
            roles
        )

    def test_max_level_profil(self, app, group_and_users):
        app.config["CODE_APPLICATION"] = "APPLI_1"
        user_of_group1 = group_and_users["user1"]
        user_no_group = group_and_users["user_no_group"]
        # cast in int for <2.0 compat
        assert int(user_of_group1.max_level_profil) == 6
        assert int(user_no_group.max_level_profil) == 1

    def test_login(self, group_and_users):
        resp = self.client.post(
            url_for("auth.login"), json={"login": "user_of_group1", "password": "admin"}
        )

        assert resp.status_code == 200
        assert "user" in resp.json
        assert "expires" in resp.json
        assert "token" in resp.json

        expires = resp.json["expires"]
        datetime_expires = datetime.fromisoformat(expires)
        # the token expiration must be tz aware to avoid issue in date comparison
        assert datetime_expires.tzinfo is not None
