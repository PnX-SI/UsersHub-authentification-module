"""unique key on t_roles.email

Revision ID: c5aed8707589
Revises: 112ccf1024ce
Create Date: 2023-05-30 11:11:59.971540

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c5aed8707589"
down_revision = "112ccf1024ce"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("t_roles_email_un", "t_roles", ["email"], schema="utilisateurs")


def downgrade():
    op.drop_constraint("t_roles_email_un", "t_roles", schema="utilisateurs")
