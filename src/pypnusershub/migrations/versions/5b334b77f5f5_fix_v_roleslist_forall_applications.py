"""fix v_roleslist_forall_applications

Revision ID: 5b334b77f5f5
Revises: 830cc8f4daef
Create Date: 2021-09-21 13:22:45.003976

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b334b77f5f5'
down_revision = '830cc8f4daef'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
DROP VIEW utilisateurs.v_userslist_forall_applications;

DROP VIEW utilisateurs.v_roleslist_forall_applications;

CREATE VIEW utilisateurs.v_roleslist_forall_applications AS
SELECT a.groupe,
    a.active,
    a.id_role,
    a.identifiant,
    a.nom_role,
    a.prenom_role,
    a.desc_role,
    a.pass,
    a.pass_plus,
    a.email,
    a.id_organisme,
    a.organisme,
    a.id_unite,
    a.remarques,
    a.date_insert,
    a.date_update,
    max(a.id_droit) AS id_droit_max,
    a.id_application
   FROM ( SELECT u.groupe,
            u.id_role,
            u.identifiant,
            u.nom_role,
            u.prenom_role,
            u.desc_role,
            u.pass,
            u.pass_plus,
            u.email,
            u.id_organisme,
            u.active,
            o.nom_organisme AS organisme,
            0 AS id_unite,
            u.remarques,
            u.date_insert,
            u.date_update,
            c.id_profil AS id_droit,
            c.id_application
           FROM utilisateurs.t_roles u
             JOIN utilisateurs.cor_role_app_profil c ON c.id_role = u.id_role
             LEFT JOIN utilisateurs.bib_organismes o ON o.id_organisme = u.id_organisme
        UNION
         SELECT u.groupe,
            u.id_role,
            u.identifiant,
            u.nom_role,
            u.prenom_role,
            u.desc_role,
            u.pass,
            u.pass_plus,
            u.email,
            u.id_organisme,
            u.active,
            o.nom_organisme AS organisme,
            0 AS id_unite,
            u.remarques,
            u.date_insert,
            u.date_update,
            c.id_profil AS id_droit,
            c.id_application
           FROM utilisateurs.t_roles u
             JOIN utilisateurs.cor_roles g ON g.id_role_utilisateur = u.id_role OR g.id_role_groupe = u.id_role
             JOIN utilisateurs.cor_role_app_profil c ON c.id_role = g.id_role_groupe
             LEFT JOIN utilisateurs.bib_organismes o ON o.id_organisme = u.id_organisme
          ) a
  WHERE a.active = true
  GROUP BY a.groupe, a.active, a.id_role, a.identifiant, a.nom_role, a.prenom_role, a.desc_role, a.pass, a.pass_plus, a.email, a.id_organisme, a.organisme, a.id_unite, a.remarques, a.date_insert, a.date_update, a.id_application;

CREATE VIEW utilisateurs.v_userslist_forall_applications
AS SELECT d.groupe,
    d.active,
    d.id_role,
    d.identifiant,
    d.nom_role,
    d.prenom_role,
    d.desc_role,
    d.pass,
    d.pass_plus,
    d.email,
    d.id_organisme,
    d.organisme,
    d.id_unite,
    d.remarques,
    d.date_insert,
    d.date_update,
    d.id_droit_max,
    d.id_application
   FROM utilisateurs.v_roleslist_forall_applications d
  WHERE d.groupe = false;
    """)


def downgrade():
    op.execute("""
DROP VIEW utilisateurs.v_userslist_forall_applications;

DROP VIEW utilisateurs.v_roleslist_forall_applications;

CREATE VIEW utilisateurs.v_roleslist_forall_applications AS
SELECT a.groupe,
    a.active,
    a.id_role,
    a.identifiant,
    a.nom_role,
    a.prenom_role,
    a.desc_role,
    a.pass,
    a.pass_plus,
    a.email,
    a.id_organisme,
    a.organisme,
    a.id_unite,
    a.remarques,
    a.date_insert,
    a.date_update,
    max(a.id_droit) AS id_droit_max,
    a.id_application
   FROM ( SELECT u.groupe,
            u.id_role,
            u.identifiant,
            u.nom_role,
            u.prenom_role,
            u.desc_role,
            u.pass,
            u.pass_plus,
            u.email,
            u.id_organisme,
            u.active,
            o.nom_organisme AS organisme,
            0 AS id_unite,
            u.remarques,
            u.date_insert,
            u.date_update,
            c.id_profil AS id_droit,
            c.id_application
           FROM utilisateurs.t_roles u
             JOIN utilisateurs.cor_role_app_profil c ON c.id_role = u.id_role
             JOIN utilisateurs.bib_organismes o ON o.id_organisme = u.id_organisme
        UNION
         SELECT u.groupe,
            u.id_role,
            u.identifiant,
            u.nom_role,
            u.prenom_role,
            u.desc_role,
            u.pass,
            u.pass_plus,
            u.email,
            u.id_organisme,
            u.active,
            o.nom_organisme AS organisme,
            0 AS id_unite,
            u.remarques,
            u.date_insert,
            u.date_update,
            c.id_profil AS id_droit,
            c.id_application
           FROM utilisateurs.t_roles u
             JOIN utilisateurs.cor_roles g ON g.id_role_utilisateur = u.id_role OR g.id_role_groupe = u.id_role
             JOIN utilisateurs.cor_role_app_profil c ON c.id_role = g.id_role_groupe
             LEFT JOIN utilisateurs.bib_organismes o ON o.id_organisme = u.id_organisme
          ) a
  WHERE a.active = true
  GROUP BY a.groupe, a.active, a.id_role, a.identifiant, a.nom_role, a.prenom_role, a.desc_role, a.pass, a.pass_plus, a.email, a.id_organisme, a.organisme, a.id_unite, a.remarques, a.date_insert, a.date_update, a.id_application;

CREATE VIEW utilisateurs.v_userslist_forall_applications
AS SELECT d.groupe,
    d.active,
    d.id_role,
    d.identifiant,
    d.nom_role,
    d.prenom_role,
    d.desc_role,
    d.pass,
    d.pass_plus,
    d.email,
    d.id_organisme,
    d.organisme,
    d.id_unite,
    d.remarques,
    d.date_insert,
    d.date_update,
    d.id_droit_max,
    d.id_application
   FROM utilisateurs.v_roleslist_forall_applications d
  WHERE d.groupe = false;
    """)
