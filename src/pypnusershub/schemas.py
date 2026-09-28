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


class UserSchema(SmartRelationshipsMixin, ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        include_fk = True
        load_instance = True
        sqla_session = db.session
        exclude = (
            "_password",
            "_password_plus",
            "champs_addi",
            "max_level_profil",
            "api_secret",
            "api_key",
        )

    # Personal / administrative fields hidden by default to avoid leaking them
    # when a user is nested in another schema. Request them explicitly with
    # only=["+email", ...] (or list them in `only`).
    # NB: do not move them to Meta.exclude: fields excluded at Meta level are not
    # generated at all and SmartRelationshipsMixin mutates opts.exclude.
    email = ma.auto_field(metadata={"exclude": True})
    identifiant = ma.auto_field(metadata={"exclude": True})
    remarques = ma.auto_field(metadata={"exclude": True})
    desc_role = ma.auto_field(metadata={"exclude": True})
    date_insert = ma.auto_field(metadata={"exclude": True})
    date_update = ma.auto_field(metadata={"exclude": True})
    active = ma.auto_field(metadata={"exclude": True})
    groupe = ma.auto_field(metadata={"exclude": True})

    # hidden by default (computed with an extra query), request it with "+max_level_profil"
    max_level_profil = fields.Integer(metadata={"exclude": True})
    nom_complet = fields.String()
    groups = fields.Nested(lambda: UserSchema, many=True)
    organisme = fields.Nested(OrganismeSchema)
    providers = fields.Nested(ProviderSchema, many=True)

    # TODO: remove this and fix usage of the schema
    @pre_load
    def make_observer(self, data, **kwargs):
        if isinstance(data, int):
            return dict({"id_role": data})
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
