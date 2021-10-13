"""get_id_role_by_name()

Revision ID: 10e87bc144cd
Revises: 951b8270a1cf
Create Date: 2021-10-07 17:20:59.521063

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '10e87bc144cd'
down_revision = '951b8270a1cf'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE FUNCTION utilisateurs.get_id_role_by_name(roleName character varying)
        RETURNS integer
        LANGUAGE plpgsql
        IMMUTABLE
    AS $BODY$
        BEGIN
            RETURN (
                SELECT id_role
                FROM utilisateurs.t_roles
                WHERE nom_role = roleName
            );
        END;
    $BODY$ ;
    """)


def downgrade():
    op.execute("DROP FUNCTION utilisateurs.get_id_role_by_name(character varying)")
