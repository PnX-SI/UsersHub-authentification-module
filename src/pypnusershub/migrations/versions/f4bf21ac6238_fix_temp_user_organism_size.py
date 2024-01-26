"""fix temp user organism size

Revision ID: f4bf21ac6238
Revises: 112ccf1024ce
Create Date: 2023-06-30 15:02:59.198157

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4bf21ac6238"
down_revision = "112ccf1024ce"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE utilisateurs.temp_users ALTER COLUMN organisme TYPE VARCHAR (250);"
    )
    pass


def downgrade():
    pass
