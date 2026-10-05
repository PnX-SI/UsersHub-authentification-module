import datetime

from typing import Any

from flask import current_app
from marshmallow import pre_load, fields

from utils_flask_sqla.schema import SmartRelationshipsMixin

from pypnusershub.env import ma, db
from pypnusershub.db.models import User, Organisme, Provider
from pypnusershub.db.tools import encode_token


class OrganismeSchema(SmartRelationshipsMixin, ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Organisme
        load_instance = True
        sqla_session = db.session


class ProviderSchema(SmartRelationshipsMixin, ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Provider
        load_instance = True
        sqla_session = db.session


class UserSafeSchema(SmartRelationshipsMixin, ma.SQLAlchemyAutoSchema):
    """Minimal public representation of a user (no email, organism, groups, etc.)."""

    class Meta:
        model = User
        load_instance = True
        sqla_session = db.session
        fields = ("id_role", "nom_complet", "organisme")
        exclude = ()

    nom_complet = fields.String(dump_only=True)
    organisme = fields.Nested(
        "OrganismeSchema", only=("nom_organisme",), dump_only=True
    )


class UserSensitiveSchema(UserSafeSchema):
    """
    Private representation of a user (includes email, organism, groups, etc.). Must only be used to show information
    to current user.
    """

    class Meta(UserSafeSchema.Meta):
        include_fk = True
        fields = UserSafeSchema.Meta.fields + (
            "nom_role",
            "prenom_role",
            "uuid_role",
            "groupe",
            "identifiant",
            "desc_role",
            "email",
            "id_organisme",
            "remarques",
            "date_insert",
            "date_update",
            "active",
            "max_level_profil",
            "groups",
            "providers",
        )

    max_level_profil = fields.Integer()
    groups = fields.Nested(lambda: UserSensitiveSchema, many=True)
    organisme = fields.Nested(OrganismeSchema)
    providers = fields.Nested(ProviderSchema, many=True)

    # TODO: remove this and fix usage of the schema
    @pre_load
    def make_observer(self, data, **kwargs):
        if isinstance(data, int):
            return {"id_role": data}
        return data

    def dump_with_token(self, obj):
        """
        Dumps user information with a JWT token and its expiration date.

        Parameters
        ----------
        obj : User
            The user object to dump.

        Returns
        -------
        dict
            A dictionary with the user information and the token. The token is
            encoded using the user's information and the secret key from the
            current Flask application configuration. The dictionary also
            contains the expiration date of the token.
        """
        user_dict = self.dump(obj)
        token_exp = datetime.datetime.now(datetime.timezone.utc)
        token_exp += datetime.timedelta(seconds=current_app.config["COOKIE_EXPIRATION"])
        return {
            "user": user_dict,
            "token": encode_token(user_dict),
            "expires": token_exp.isoformat(),
        }
