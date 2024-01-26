"""add unique constraint on t_roles UUID

Revision ID: 112ccf1024ce
Revises: 10e87bc144cd
Create Date: 2022-04-28 10:35:41.272095

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "112ccf1024ce"
down_revision = "10e87bc144cd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "t_roles_uuid_un", "t_roles", ["uuid_role"], schema="utilisateurs"
    )


def downgrade():
    op.drop_constraint("t_roles_uuid_un", "t_roles", schema="utilisateurs")
