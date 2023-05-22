"""add unique constraint on email_role

Revision ID: 36998af706d1
Revises: 112ccf1024ce
Create Date: 2023-03-09 11:18:14.006181

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '36998af706d1'
down_revision = '112ccf1024ce'
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        constraint_name="t_roles_email_un",
        table_name="t_roles",
        columns=["email"],
        schema="utilisateurs"
    )


def downgrade():
    op.drop_constraint(
        constraint_name="t_roles_email_un",
        table_name="t_roles",
        schema="utilisateurs"
        )
