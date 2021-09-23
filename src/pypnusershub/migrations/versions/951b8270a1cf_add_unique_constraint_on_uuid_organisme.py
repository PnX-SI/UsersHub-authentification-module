"""add unique constraint on bib_organismes.uuid_organisme

Revision ID: 951b8270a1cf
Revises: 5b334b77f5f5
Create Date: 2021-09-23 09:44:23.613575

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '951b8270a1cf'
down_revision = '5b334b77f5f5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint('bib_organismes_un', 'bib_organismes', ['uuid_organisme'], schema='utilisateurs')


def downgrade():
    op.drop_constraint('bib_organismes_un', 'bib_organismes', schema='utilisateurs')
