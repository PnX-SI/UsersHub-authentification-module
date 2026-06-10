from pypnusershub.schemas import OrganismeSchema
from pypnusershub.db import db
from pypnusershub.db.models import Organisme


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
    organism = db.session.merge(organism)
    db.session.commit()
    return organism_schema.dump(organism)


def delete_organism(id_organisme: int) -> None:
    """
    Delete an organism.

    Parameters
    ----------
    id_organisme : int
        The ID of the organism to delete.

    Raises
    ------
    ValueError
        If the organism with the given ID does not exist.
    """
    organism = db.session.get(Organisme, id_organisme)
    if organism is None:
        raise ValueError(f"Organism with id {id_organisme} does not exist")
    db.session.delete(organism)
    db.session.commit()
