"""add apikey to t_roles

Revision ID: 17122ba73a6f
Revises: b3dec57f13d8
Create Date: 2025-06-03 20:01:52.252581

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "17122ba73a6f"
down_revision = "b3dec57f13d8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        column=sa.Column("api_key", sa.UnicodeText(), server_default=None, unique=True),
        table_name="t_roles",
        schema="utilisateurs",
    )
    op.add_column(
        column=sa.Column("api_secret", sa.UnicodeText(), server_default=None),
        table_name="t_roles",
        schema="utilisateurs",
    )


def downgrade():
    op.drop_column(column_name="api_key", table_name="t_roles", schema="utilisateurs")
    op.drop_column(
        column_name="api_secret", table_name="t_roles", schema="utilisateurs"
    )
