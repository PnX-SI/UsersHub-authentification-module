from pypnusershub.db.models import Organisme, User
import pytest

from pypnusershub.routes import insert_or_update_organism, insert_or_update_role
from pypnusershub.schemas import OrganismeSchema, UserSchema
from pypnusershub.tests.fixtures import organism

@pytest.mark.usefixtures("client_class", "temporary_transaction")
class TestUtilisateurs:
    def test_insert_user(self, organism):
        user_schema = UserSchema(exclude=["nom_complet"])
        group = User.query.get(1001)

        user = {
            "id_role": 99999,
            "identifiant": "test.user",
            "nom_role": "test",
            "prenom_role": "test",
            "id_organisme": organism.id_organisme,
            "email": "test@test.fr",
            "active": True,
            "groups": [user_schema.dump(group)],

        }
        insert_or_update_role(user)
        user["identifiant"] = "update"
        insert_or_update_role(user)
        created_user = User.query.get(99999)
        user_schema = UserSchema(only=["groups"])
        created_user_as_dict = user_schema.dump(created_user)
        assert created_user_as_dict["identifiant"] == "update"
        assert created_user_as_dict["id_role"] == 99999
        assert len(created_user_as_dict["groups"]) == 1

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

        create_organism = Organisme.query.get(99999)
        organism_schema = OrganismeSchema()
        organism_as_dict = organism_schema.dump(create_organism)
        assert organism_as_dict["nom_organisme"] == "update"


