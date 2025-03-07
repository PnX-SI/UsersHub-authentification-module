import click
from flask.cli import with_appcontext
import sqlalchemy as sa

from pypnusershub.db.models import User
from pypnusershub.env import db


@click.group(help="User management commands")
def user():
    pass


@user.command()
@click.argument("identifiant")
@click.argument("password")
@click.option("--group", help="Group of the user")
@click.option("--prenom_role", help="Prenom of the user")
@click.option("--nom_role", help="Nom of the user")
@with_appcontext
def add(identifiant, password, group, prenom_role, nom_role):
    """
    Add a new user

    Parameters
    ----------
    identifiant : str
        the username of the user
    password : str
        the password of the user
    group : str, optional
        the group of the user
    prenom_role : str, optional
        the prenom of the user
    nom_role : str, optional
        the nom of the user

    Raises
    ------
    click.UsageError
        if the user already exists
    """
    if not identifiant or not password:
        raise click.UsageError("Both identifiant and password are required.")

    existing_user = db.session.scalar(
        sa.exists().where(User.identifiant == identifiant).select()
    )
    if existing_user:
        raise click.UsageError(f"User {identifiant} already exists")

    # If prenom_role or nom_role is not provided, build them from the identifiant
    if not prenom_role or not nom_role:
        parts = identifiant.split(".")
        if len(parts) == 2:
            prenom_role = prenom_role or parts[0].capitalize()
            nom_role = nom_role or parts[1].capitalize()

    user = User(
        identifiant=identifiant,
        prenom_role=prenom_role,
        nom_role=nom_role,
    )

    user.password = password
    if group:
        group_ = db.session.execute(
            sa.select(User).filter_by(groupe=True, nom_role=group)
        ).scalar_one_or_none()
        if group_:
            user.groups.append(group_)
    db.session.add(user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise click.ClickException(f"Failed to add user: {e}")


@user.command()
@click.argument("identifiant")
@click.option(
    "--password", prompt="New password", confirmation_prompt=True, hide_input=True
)
@with_appcontext
def change_password(identifiant, password):
    """
    Change a user's password.

    Parameters
    ----------
    identifiant : str
        the username (login) of the user whose password will be changed
    password : str
        the new password

    Notes
    -----
    This command is meant to be used from the command line, not from python.
    """
    user = db.session.execute(
        sa.select(User).filter_by(identifiant=identifiant)
    ).scalar_one_or_none()
    if user is None:
        raise click.UsageError(f"User {identifiant} does not exist")
    user.password = password
    db.session.commit()


@user.command()
@click.argument("identifiant")
@click.option("-y", "--yes", is_flag=True, help="Do not ask for confirmation")
@with_appcontext
def remove(identifiant, yes):
    """
    Remove a user.

    Parameters
    ----------
    identifiant : str
        the username (login) of the user to remove
    -y, --yes : flag
        Do not ask for confirmation

    """
    if not yes:
        click.confirm(
            "Are you sure you want to remove user %s?" % identifiant, abort=True
        )
    user = db.session.execute(
        sa.select(User).filter_by(identifiant=identifiant)
    ).scalar_one_or_none()
    if user is None:
        raise click.UsageError(f"User {identifiant} does not exist")
    db.session.delete(user)
    db.session.commit()
