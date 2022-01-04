from pypnusershub.env import db
from pypnusershub.db.models import Organisme
import pytest

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

@pytest.fixture(scope='function')
def organism(app):
    with db.session.begin_nested():
        org = Organisme(nom_organisme="test")
        db.session.add(org)
    return org