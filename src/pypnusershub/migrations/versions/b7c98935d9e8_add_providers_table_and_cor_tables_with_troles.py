"""add provider table and correspondances table with t_roles

Revision ID: b7c98935d9e8
Revises: f9d3b95946cd
Create Date: 2024-04-04 10:35:44.745906

"""

from alembic import op
import sqlalchemy as sa

from pypnusershub.db.models import Provider


# revision identifiers, used by Alembic.
revision = "b7c98935d9e8"
down_revision = "f9d3b95946cd"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "t_providers",
        sa.Column("id_provider", sa.Integer, primary_key=True),
        sa.Column(
            "name", sa.Unicode, nullable=False, comment="Nom de l'instance du provider"
        ),
        sa.Column(
            "url",
            sa.Unicode,
            nullable=True,
            comment="L'url du fournisseur d'authentification",
        ),
        schema="utilisateurs",
    )
    op.create_table(
        "cor_role_provider",
        sa.Column(
            "id_role",
            sa.Integer,
            sa.ForeignKey("utilisateurs.t_roles.id_role"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "id_provider",
            sa.Integer,
            sa.ForeignKey("utilisateurs.t_providers.id_provider"),
            nullable=False,
            primary_key=True,
        ),
        schema="utilisateurs",
        comment="Table de correpondance entre t_roles et t_providers",
    )
    op.execute(sa.insert(Provider).values(name="local_provider"))


def downgrade():
    op.drop_table("cor_role_provider", schema="utilisateurs")
    op.drop_table("t_providers", schema="utilisateurs")
