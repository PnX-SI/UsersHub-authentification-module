"""add drop on cascade on cor_role_provider.id_role

Revision ID: b3dec57f13d8
Revises: cf38131bc247
Create Date: 2025-03-04 16:39:07.647866

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b3dec57f13d8"
down_revision = "cf38131bc247"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
ALTER TABLE utilisateurs.cor_role_provider DROP CONSTRAINT cor_role_provider_id_role_fkey;
ALTER TABLE utilisateurs.cor_role_provider ADD CONSTRAINT cor_role_provider_id_role_fkey FOREIGN KEY (id_role) REFERENCES utilisateurs.t_roles(id_role) ON DELETE CASCADE;

    """
    )


def downgrade():
    op.execute(
        """
ALTER TABLE utilisateurs.cor_role_provider DROP CONSTRAINT cor_role_provider_id_role_fkey;
ALTER TABLE utilisateurs.cor_role_provider ADD CONSTRAINT cor_role_provider_id_role_fkey FOREIGN KEY (id_role) REFERENCES utilisateurs.t_roles(id_role);
    """
    )
