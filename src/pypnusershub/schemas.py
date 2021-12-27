from marshmallow import pre_load, fields

from utils_flask_sqla.schema import SmartRelationshipsMixin

from pypnusershub.env import MA 
from pypnusershub.db.models import User, Organisme


class UserSchema(SmartRelationshipsMixin, MA.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        exclude = (
            "_password",
            "_password_plus",
            "active",
            "date_insert",
            "date_update",
            "desc_role",
            "email",
            "groupe",
            "remarques",
            "identifiant",
        )

    nom_complet = fields.String()

    # TODO: remove this and fix usage of the schema
    @pre_load
    def make_observer(self, data, **kwargs):
        if isinstance(data, int):
            return dict({"id_role": data})
        return data


class OrganismeSchema(SmartRelationshipsMixin, MA.SQLAlchemyAutoSchema):
    class Meta:
        model = Organisme
        load_instance = True
