"""[t_roles] add unique constraint on the identifiant field

Revision ID: 532ddbc066a2
Revises: 17122ba73a6f
Create Date: 2026-01-21 11:22:08.272033

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "532ddbc066a2"
down_revision = "17122ba73a6f"
branch_labels = None
depends_on = None


def upgrade():
    try:
        op.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_t_roles_identifiant
            ON utilisateurs.t_roles (identifiant)
            WHERE identifiant != '' AND identifiant IS NOT NULL;
            """)
    except sa.exc.IntegrityError as e:
        print(
            "Impossible de créer la contrainte d'unicité 'uq_t_roles_identifiant' sur la table 't_roles'. "
            "Cela peut être dû aux valeurs dupliquées existantes dans le champ 'utilisateurs.t_roles.identifiant'."
        )
        raise e


def downgrade():
    op.drop_constraint(
        "uq_t_roles_identifiant", "t_roles", type_="unique", schema="utilisateurs"
    )
