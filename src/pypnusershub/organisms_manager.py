from pypnusershub.schemas import OrganismeSchema
from pypnusershub.db import db

def insert_or_update_organism(organism) -> dict:
    """
    Insert an organism.

    The organism may eventually be updated rather than inserted.

    Parameters
    ----------
    organism : dict
        A dictionary containing the organism data.

    Returns
    -------
    dict
        The inserted or updated organism.
    """
    organism_schema = OrganismeSchema()
    organism = organism_schema.load(organism)
    db.session.add(organism)
    db.session.commit()
    return organism_schema.dump(organism)