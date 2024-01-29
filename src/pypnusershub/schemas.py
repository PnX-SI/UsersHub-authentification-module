from marshmallow import pre_load, fields

from utils_flask_sqla.schema import SmartRelationshipsMixin

from pypnusershub.env import ma, db
from pypnusershub.db.models import User, Organisme


class OrganismeSchema(SmartRelationshipsMixin, ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Organisme
        load_instance = True
        sqla_session = db.session


class UserSchema(SmartRelationshipsMixin, ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_fk = True
        load_instance = True
        sqla_session = db.session
        exclude = ("_password", "_password_plus", "champs_addi", "max_level_profil")

    max_level_profil = fields.Integer()
    nom_complet = fields.String()
    groups = fields.Nested(lambda: UserSchema, many=True)
    organisme = fields.Nested(OrganismeSchema)

    # TODO: remove this and fix usage of the schema
    @pre_load
    def make_observer(self, data, **kwargs):
        if isinstance(data, int):
            return dict({"id_role": data})
        return data
