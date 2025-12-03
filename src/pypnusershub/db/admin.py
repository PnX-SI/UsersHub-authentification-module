from flask_admin.contrib.sqla import ModelView


class BibOrganismesAdmin(ModelView):
    page_size = 10
    column_list = [
        "id_organisme",
        "uuid_organisme",
        "nom_organisme",
        "adresse_organisme",
        "cp_organisme",
        "ville_organisme",
        "tel_organisme",
        "fax_organisme",
        "email_organisme",
        "url_organisme",
        "url_logo",
        "id_parent",
        "additional_data",
        "meta_create_date",
        "meta_update_date",
    ]
    column_labels = {
        "id_organisme": "ID",
        "uuid_organisme": "UUID",
        "nom_organisme": "Nom",
        "adresse_organisme": "Adresse",
        "cp_organisme": "Code postal",
        "ville_organisme": "Ville",
        "tel_organisme": "Téléphone",
        "fax_organisme": "Fax",
        "email_organisme": "E-mail",
        "url_organisme": "URL du site web",
        "url_logo": "URL du logo",
        "id_parent": "ID de l'organisme parent",
        "additional_data": "Informations additionnelles",
        "meta_create_date": "Date de création en BDD",
        "meta_update_date": "Date de mise à jour en BDD",
    }
    # members ?
    column_display_pk = True
    form_columns = [
        "nom_organisme",
        "adresse_organisme",
        "cp_organisme",
        "ville_organisme",
        "tel_organisme",
        "fax_organisme",
        "email_organisme",
        "url_organisme",
        "url_logo",
    ]
