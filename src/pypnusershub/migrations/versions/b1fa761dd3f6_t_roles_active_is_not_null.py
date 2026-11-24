"""[t_roles] active is not null

Revision ID: b1fa761dd3f6
Revises: 532ddbc066a2
Create Date: 2026-11-23 17:17:22.133513

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b1fa761dd3f6"
down_revision = "532ddbc066a2"
branch_labels = None
depends_on = None


def upgrade():
    # A NULL `active` already prevented any local login (and is now treated as
    # inactive by `User.is_active`): keep that effective state explicit.
    op.execute("UPDATE utilisateurs.t_roles SET active = false WHERE active IS NULL;")
    op.execute("""
        ALTER TABLE utilisateurs.t_roles
            ALTER COLUMN active SET DEFAULT true,
            ALTER COLUMN active SET NOT NULL;
        """)


def downgrade():
    op.execute("ALTER TABLE utilisateurs.t_roles ALTER COLUMN active DROP NOT NULL;")
