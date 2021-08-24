"""utilisateurs schema 1.4.7

Revision ID: fa35dfe5ff27
Revises: 
Create Date: 2021-08-24 15:39:57.784074

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa35dfe5ff27'
down_revision = None
branch_labels = ('utilisateurs',)
depends_on = None


def upgrade():
    raise Exception("""
    You should manually migrate your database to 1.4.7 version of utilisateurs schema, then stamp your database version to this revision :
        flask db stamp fa35dfe5ff27
    """)


def downgrade():
    raise Exception("""
    This revision do not support downgrade (yet).
    """)
