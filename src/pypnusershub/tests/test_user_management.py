import pytest
from datetime import datetime
import sqlalchemy as sa

from pypnusershub.db import db
from pypnusershub.db.models import (
    User,
    TempUser,
    CorRoleToken,
    UserApplicationRight,
)
from pypnusershub.auth.subscribe import (
    generate_token,
    create_cor_role_token,
    create_temp_user,
    valid_temp_user,
    change_password,
)

from .fixtures import group_and_users, applications, profils


def test_generate_token_random():
    """Token should be a random 128-bit string"""
    token1 = generate_token()
    token2 = generate_token()
    assert isinstance(token1, str)
    assert token1 != token2
    assert len(token1) > 0


# ===============================================================
# FIXTURES
# ===============================================================


@pytest.fixture(scope="function")
def temp_user_fixture(applications):
    """Create a real TempUser for validation tests"""
    with db.session.begin_nested():
        temp_user = TempUser(
            identifiant="tmp_user",
            password="hashedpw",
            pass_md5="hashedpw",
            token_role="token_123",
            date_insert=datetime.now(),
            email="temp@test.com",
            id_application=applications["app1"].id_application,
            groupe=False,
        )
        db.session.add(temp_user)
    return temp_user


# ===============================================================
# create_cor_role_token
# ===============================================================


def test_create_cor_role_token_no_email():
    with pytest.raises(Exception, match="No email was found"):
        create_cor_role_token(None)


def test_create_cor_role_token_user_not_found():
    with pytest.raises(KeyError, match="No user was found "):
        create_cor_role_token("unknown@test.com")


def test_create_cor_role_token_success(group_and_users):
    user = group_and_users["user1"]
    user.email = "user@test.com"
    db.session.flush()

    result = create_cor_role_token("user@test.com")

    assert "token" in result
    assert result["id_role"] == user.id_role

    # Verify the token saved in DB
    cor_token = db.session.scalars(
        sa.select(CorRoleToken).where(CorRoleToken.id_role == user.id_role)
    ).first()
    assert cor_token is not None
    assert cor_token.token == result["token"]


# ===============================================================
# create_temp_user
# ===============================================================


def test_create_temp_user_password_mismatch(app):
    """Should raise when password != confirmation"""
    data = {
        "identifiant": "temp1",
        "password": "abc",
        "password_confirmation": "xyz",
        "email": "temp1@test.com",
    }
    with app.app_context():
        with pytest.raises(Exception, match="Password and password_confirmation"):
            create_temp_user(data)


def test_create_temp_user_success(app, applications):
    """Should create and return a token for new temp user"""
    data = {
        "identifiant": "temp2",
        "password": "mypw",
        "password_confirmation": "mypw",
        "email": "temp2@test.com",
        "id_application": applications["app1"].id_application,
        "groupe": False,
    }
    app.config["PASS_METHOD"] = "md5"

    with db.session.begin_nested():
        result = create_temp_user(data)
    assert "token" in result

    # Ensure user is persisted
    tu = db.session.scalar(sa.select(TempUser).where(TempUser.identifiant == "temp2"))
    assert tu is not None
    assert tu.token_role == result["token"]


# ===============================================================
# valid_temp_user
# ===============================================================


def test_valid_temp_user_no_user(app):
    """Should raise when token doesn't match any TempUser"""
    with pytest.raises(Exception, match="Il n'y a pas d'utilisateur temporaire"):
        valid_temp_user({"token": "badtoken", "id_application": 1})


def test_valid_temp_user_success(app, temp_user_fixture, applications):
    """Convert a TempUser to a real User"""
    # Create an application default right to simulate group
    with db.session.begin_nested():
        default_group = User(groupe=True, identifiant="default_group")
        db.session.add(default_group)
        db.session.flush()

        db.session.add(
            UserApplicationRight(
                id_role=default_group.id_role,
                id_profil=1,
                id_application=applications["app1"].id_application,
            )
        )
        db.session.flush()

    # Monkeypatch get_default_for_app with safe scalar
    def fake_default_for_app(app_id):
        return db.session.scalars(
            sa.select(UserApplicationRight).where(
                UserApplicationRight.id_application == app_id
            )
        ).first()

    UserApplicationRight.get_default_for_app = staticmethod(fake_default_for_app)

    result = valid_temp_user(
        {
            "token": temp_user_fixture.token_role,
            "id_application": applications["app1"].id_application,
        }
    )

    assert "identifiant" in result
    assert result["identifiant"] == temp_user_fixture.identifiant

    # TempUser should be deleted
    tu = db.session.scalar(
        sa.select(TempUser).where(TempUser.token_role == temp_user_fixture.token_role)
    )
    assert tu is None


# ===============================================================
# change_password
# ===============================================================


def test_change_password_missing_token(app):
    with pytest.raises(ValueError, match="Token non défini"):
        change_password(None, "a", "a")


def test_change_password_missing_password(app):
    with pytest.raises(ValueError, match="Password non défini"):
        change_password("tok", None, None)


def test_change_password_token_not_found(app):
    with pytest.raises(ValueError, match="Pas d'id role associée"):
        change_password("invalid", "pw", "pw")


def test_change_password_success(app, group_and_users):
    """Valid case: updates password and deletes token"""
    user = group_and_users["user1"]
    token = "tok123"

    # Clean any existing tokens for this user to avoid duplicates
    db.session.query(CorRoleToken).filter_by(id_role=user.id_role).delete()
    db.session.flush()

    db.session.add(CorRoleToken(id_role=user.id_role, token=token))
    db.session.flush()

    result = change_password(token, "newpw", "newpw")
    assert result["identifiant"] == user.identifiant

    # Ensure CorRoleToken deleted
    cors = db.session.scalars(
        sa.select(CorRoleToken).where(CorRoleToken.token == token)
    ).first()
    assert cors is None
