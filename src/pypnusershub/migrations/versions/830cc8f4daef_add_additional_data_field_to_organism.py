"""add additional_data field to bib_organismes

Revision ID: 830cc8f4daef
Revises: fa35dfe5ff27
Create Date: 2021-09-06 13:18:28.276081

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '830cc8f4daef'
down_revision = 'fa35dfe5ff27'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'bib_organismes',
        sa.Column('additional_data', JSONB, server_default='{}'),
        schema='utilisateurs'
    )


def downgrade():
    op.drop_column(
        'bib_organismes',
        'additional_data',
        schema='utilisateurs'
    )
