"""Add meta create/insert date to biborganismes

Revision ID: cf38131bc247
Revises: f9d3b95946cd
Create Date: 2024-05-20 10:45:25.067157

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "cf38131bc247"
down_revision = "f9d3b95946cd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "bib_organismes",
        sa.Column("meta_create_date", sa.TIMESTAMP, server_default=sa.func.now()),
        schema="utilisateurs",
    )
    op.add_column(
        "bib_organismes",
        sa.Column("meta_update_date", sa.TIMESTAMP, server_default=sa.func.now()),
        schema="utilisateurs",
    )
    op.execute(
        """
CREATE FUNCTION utilisateurs.fct_trg_meta_dates_change() RETURNS trigger
    LANGUAGE plpgsql
AS
$$
begin
        if(TG_OP = 'INSERT') THEN
                NEW.meta_create_date = NOW();
        ELSIF(TG_OP = 'UPDATE') THEN
                NEW.meta_update_date = NOW();
                if(NEW.meta_create_date IS NULL) THEN
                        NEW.meta_create_date = NOW();
                END IF;
        end IF;
        return NEW;
end;
$$;

CREATE TRIGGER tri_meta_dates_change_organisms
    BEFORE INSERT OR UPDATE
    ON utilisateurs.bib_organismes
    FOR EACH ROW
EXECUTE PROCEDURE utilisateurs.fct_trg_meta_dates_change();
               """
    )


def downgrade():
    op.drop_column(
        table_name="bib_organismes",
        column_name="meta_create_date",
        schema="utilisateurs",
    )
    op.drop_column(
        table_name="bib_organismes",
        column_name="meta_update_date",
        schema="utilisateurs",
    )
    op.execute(
        """
DROP TRIGGER tri_meta_dates_change_organisms ON utilisateurs.bib_organismes;
DROP FUNCTION utilisateurs.fct_trg_meta_dates_change();
               """
    )
