"""set code_profil in integer

Revision ID: f9d3b95946cd
Revises: f4bf21ac6238
Create Date: 2023-09-13 10:00:16.065637

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f9d3b95946cd"
down_revision = "f4bf21ac6238"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        alter table utilisateurs.t_profils 
        alter column code_profil type integer using code_profil::integer;
        """
    )


def downgrade():
    op.execute(
        """
        alter table utilisateurs.t_profils 
        alter column code_profil type character varying(10) using code_profil::text;
        """
    )
