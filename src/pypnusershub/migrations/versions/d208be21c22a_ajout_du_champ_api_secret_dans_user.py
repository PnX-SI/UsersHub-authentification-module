"""Ajout du champ api_secret dans User

Revision ID: d208be21c22a
Revises: 17122ba73a6f
Create Date: 2025-06-04 16:39:28.167692

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd208be21c22a'
down_revision = '17122ba73a6f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        column=sa.Column("api_secret", sa.UnicodeText(), server_default=None, unique=True),
        table_name="t_roles",
        schema="utilisateurs",
    )


def downgrade():
    op.drop_column(column_name="api_secret", table_name="t_roles", schema="utilisateurs")
