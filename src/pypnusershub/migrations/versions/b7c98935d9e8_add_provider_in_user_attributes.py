"""add provider in user attributes 

Revision ID: b7c98935d9e8
Revises: f9d3b95946cd
Create Date: 2024-04-04 10:35:44.745906

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7c98935d9e8"
down_revision = "f9d3b95946cd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "t_roles",
        sa.Column(
            "provider",
            sa.Unicode,
            nullable=False,
            server_default=sa.text("default"),
        ),
        schema="utilisateurs",
    )


def downgrade():
    op.drop_column("t_roles", "provider", schema="utilisateurs")
