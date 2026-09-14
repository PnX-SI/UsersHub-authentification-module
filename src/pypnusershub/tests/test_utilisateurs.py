from datetime import datetime
from flask import url_for, session
import sqlalchemy as sa

import pytest

from pypnusershub.db.models import Organisme, User

from pypnusershub.organisms_manager import insert_or_update_organism, delete_organism
from pypnusershub.schemas import OrganismeSchema, UserSchema
from pypnusershub.tests.fixtures import *
from pypnusershub.tests.utils import set_logged_user

from sqlalchemy import select

from pypnusershub.auth.auth_manager import auth_manager, Authentication


@pytest.fixture
def provider_instance() -> Authentication:
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
        provider_instance.insert_or_update_role(user_dict)
        user_dict["identifiant"] = "update"
        provider_instance.insert_or_update_role(user_dict)
        created_user = db.session.get(User, 99999)
        user_schema = UserSchema(only=["groups"])
        created_user_as_dict = user_schema.dump(created_user)
        assert created_user_as_dict["identifiant"] == "update"
        assert created_user_as_dict["id_role"] == 99999
        assert len(created_user_as_dict["groups"]) == 1

        app.config["AUTHENTICATION"]["DEFAULT_RECONCILIATION_GROUP_ID"] = (
            group_and_users["group2"].id_role
        )
        user_dict["id_role"] = 99998
        user_dict["email"] = "test@test2.fr"
        user_dict["identifiant"] = "test2.user"
        user_ = provider_instance.insert_or_update_role(user_dict)
        assert len(db.session.get(User, 99998).groups) == 2

    def test_insert_or_update_role_duplicate_identifiant(self, provider_instance):
        """Test that inserting a user with an existing identifier raises an IntegrityError"""
        # Arrange
        user_dict = {
            "id_role": 99999,
            "identifiant": "test.user",
            "nom_role": "test",
            "prenom_role": "test",
            "email": "test@test.fr",
        }
        provider_instance.insert_or_update_role(user_dict)

        # Act & Assert
        with pytest.raises(sa.exc.IntegrityError):
            user = User(
                identifiant="test.user",
                id_role=99988,
                nom_role="dup",
                prenom_role="dup",
                email="ddd",
            )
            db.session.add(user)
            db.session.commit()

    def test_insert_or_update_role_duplicate_uuid(self, provider_instance):
        """Test that inserting a user with an existing UUID raises an IntegrityError"""
        # Arrange
        user_dict = {
            "id_role": 99999,
            "identifiant": "test.user",
            "nom_role": "test",
            "prenom_role": "test",
            "email": "test@test.fr",
        }
        user_1 = provider_instance.insert_or_update_role(user_dict)

        # Act & Assert
        with pytest.raises(sa.exc.IntegrityError):
            user_2 = User(
                uuid_role=user_1.uuid_role,
                id_role=99987,
                nom_role="dup",
                prenom_role="dup",
                email="ddd",
            )
            db.session.add(user_2)
            db.session.commit()

    def test_insert_or_update_role_grp_reconcialiation(
        self, provider_instance, group_and_users
    ):
        # test modification du local provider pour lui ajouter un group mapping
        # et un group_claim_name
        # provider_instance.configure(provider_config)
        provider_instance.group_claim_name = "provided_groups"
        provider_instance.group_mapping = {
            "group1": group_and_users["group1"].id_role,
            "group2": group_and_users["group1"].id_role,
        }

        user_to_reconcialite = {
            "id_role": 999998,
            "identifiant": "test2.user",
            "nom_role": "test2",
            "prenom_role": "test2",
            "email": "test3@test.fr",
        }

        user = provider_instance.insert_or_update_role(
            user_dict=user_to_reconcialite, source_groups=["group1", "group2"]
        )

        user_group_id = map(lambda g: g.id_role, user.groups)
        assert set(user_group_id) == {group_and_users["group1"].id_role}

    def test_insert_or_update_role_grp_reconcialiation_strict_mirror_existing_user(
        self, provider_instance, group_and_users
    ):
        provider_instance.group_mapping = {
            "group1": group_and_users["group1"].id_role,
            "group2": group_and_users["group2"].id_role,
        }

        user_dict = {
            "id_role": 999997,
            "identifiant": "mirror.user",
            "nom_role": "mirror",
            "prenom_role": "user",
            "email": "mirror@test.fr",
        }

        user = provider_instance.insert_or_update_role(
            user_dict=user_dict,
            source_groups=["group1", "group2"],
            reconciliate_attr="identifiant",
        )
        assert set(map(lambda g: g.id_role, user.groups)) == {
            group_and_users["group1"].id_role,
            group_and_users["group2"].id_role,
        }

        # Re-login with fewer source groups should remove obsolete mapped groups.
        user = provider_instance.insert_or_update_role(
            user_dict=user_dict,
            source_groups=["group2"],
            reconciliate_attr="identifiant",
        )
        assert set(map(lambda g: g.id_role, user.groups)) == {
            group_and_users["group2"].id_role
        }

    def test_insert_or_update_role_grp_reconcialiation_strict_mirror_keeps_unmanaged_groups(
        self, provider_instance, group_and_users
    ):
        provider_instance.group_mapping = {
            "group1": group_and_users["group1"].id_role,
            "group2": group_and_users["group2"].id_role,
        }

        unmanaged_group = User(groupe=True, identifiant="group_unmanaged")
        db.session.add(unmanaged_group)
        db.session.flush()

        user_dict = {
            "id_role": 999996,
            "identifiant": "mirror.user.unmanaged",
            "nom_role": "mirror",
            "prenom_role": "unmanaged",
            "email": "mirror-unmanaged@test.fr",
        }

        user = provider_instance.insert_or_update_role(
            user_dict=user_dict,
            source_groups=["group1", "group2"],
            reconciliate_attr="identifiant",
        )
        user.groups.append(unmanaged_group)
        db.session.commit()

        user = provider_instance.insert_or_update_role(
            user_dict=user_dict,
            source_groups=["group2"],
            reconciliate_attr="identifiant",
        )
        assert set(map(lambda g: g.id_role, user.groups)) == {
            group_and_users["group2"].id_role,
            unmanaged_group.id_role,
        }

    def test_insert_or_update_with_fields_to_update(
        self, provider_instance, group_and_users
    ):
        """
        Test that the fields_to_update parameter works as expected and, if filled it only updates the fields specified in the parameter.

        """
        user = group_and_users["user1"]
        user_to_reconcialite = {
            "email": user.email,
            "nom_role": "new nom",
            "prenom_role": "new prénom",
        }
        user = provider_instance.insert_or_update_role(
            user_dict=user_to_reconcialite,
            reconciliate_attr="email",
            fields_to_update=["nom_role"],
        )

        assert user.prenom_role == "prenom"
        assert user.nom_role == "new nom"

        user = provider_instance.insert_or_update_role(
            user_dict=user_to_reconcialite, reconciliate_attr="email"
        )
        assert user.prenom_role == "new prénom"
        assert user.nom_role == "new nom"

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

    def test_create_organisme_unique(self):
        organism1 = {
            "nom_organisme": "test",
            "id_organisme": 999999,
            "adresse_organisme": "66 rue du truc",
            "ville_organisme": "Gap",
            "tel_organisme": "00000000",
            "email_organisme": "test@test.com",
            "url_organisme": "http://lala.com",
            "url_logo": "http://lala.com",
            "url_logo": "http://lala.com",
        }
        insert_or_update_organism(organism1)
        organism2 = {
            "nom_organisme": "test",
            "id_organisme": 999998,
            "adresse_organisme": "66 rue du truc",
            "ville_organisme": "Gap",
            "tel_organisme": "00000000",
            "email_organisme": "test@test.com",
            "url_organisme": "http://lala.com",
            "url_logo": "http://lala.com",
            "url_logo": "http://lala.com",
        }
        with pytest.raises(sa.exc.IntegrityError):
            insert_or_update_organism(organism2)

    def test_delete_user(self):
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
        assert db.session.get(Organisme, 99999)
        delete_organism(99999)
        assert db.session.get(Organisme, 99999) is None

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
        assert session["current_provider"] == "local_provider"

        expires = resp.json["expires"]
        datetime_expires = datetime.fromisoformat(expires)
        # the token expiration must be tz aware to avoid issue in date comparison
        assert datetime_expires.tzinfo is not None

    def test_get_user_data(self, group_and_users):
        set_logged_user(self.client, group_and_users["user1"])

        response = self.client.get(url_for("auth.get_user_data"))
        assert response.status_code == 200
        data = response.json
        assert "token" in data
        assert "expires" in data
        assert "user" in data

        assert "max_level_profil" in data["user"]
        assert "providers" in data["user"]

    def test_login_exists_with_existing_user(self, group_and_users):
        """Test login_exists endpoint with an existing login"""
        response = self.client.get(url_for("auth.login_exists", login="user_of_group1"))
        assert response.status_code == 200
        assert response.json is True

    def test_login_exists_with_nonexistent_user(self, group_and_users):
        """Test login_exists endpoint with a non-existent login"""
        response = self.client.get(
            url_for("auth.login_exists", login="nonexistent_user")
        )
        assert response.status_code == 200
        assert response.json is False

    def test_login_exists_without_login_parameter(self):
        """Test login_exists endpoint without the login parameter"""
        response = self.client.get(url_for("auth.login_exists"))
        assert response.status_code == 400
        print(response.json)
        print(dir(response))
        assert "Missing 'login' parameter" in response.json["message"]
