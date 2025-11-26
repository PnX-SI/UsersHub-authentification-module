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
from pypnusershub.auth import user_manager

from .fixtures import group_and_users, applications, profils


def test_generate_token_random():
    """Token should be a random 128-bit string"""
    token1 = user_manager.generate_token()
    token2 = user_manager.generate_token()
    assert isinstance(token1, str)
    assert token1 != token2
    assert len(token1) > 0


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


class TestCreateCorRoleToken:
    def test_create_cor_role_token_no_email(self):
        with pytest.raises(
            user_manager.PrintableValueError, match="No email was found"
        ):
            user_manager.create_cor_role_token(None)

    def test_create_cor_role_token_user_not_found(self):
        with pytest.raises(
            user_manager.PrintableValueError, match="No user was found "
        ):
            user_manager.create_cor_role_token("unknown@test.com")

    def test_create_cor_role_token_success(self, group_and_users):
        user = group_and_users["user1"]
        user.email = "user@test.com"
        db.session.flush()

        result = user_manager.create_cor_role_token("user@test.com")

        assert "token" in result
        assert result["id_role"] == user.id_role

        # Verify the token saved in DB
        cor_token = db.session.scalars(
            sa.select(CorRoleToken).where(CorRoleToken.id_role == user.id_role)
        ).first()
        assert cor_token is not None
        assert cor_token.token == result["token"]


class TestCreateTempUser:
    @staticmethod
    def setup_method(self):
        user_manager.init_user_manager(0, False, False, False)

    def test_create_temp_user_password_mismatch(self, app):
        """Should raise when password != confirmation"""
        data = {
            "identifiant": "temp1",
            "password": "abc",
            "password_confirmation": "xyz",
            "email": "temp1@test.com",
        }
        with app.app_context():
            with pytest.raises(Exception, match="Password and password_confirmation"):
                user_manager.create_temp_user(data)

    def test_create_temp_user_invalid_password(self, app):
        """Should raise when password does not match criteria."""
        user_manager.init_user_manager(
            8, True, True, True
        )  # Enforce stronger password rules
        data = {
            "identifiant": "temp1",
            "password": "short",  # Too short
            "password_confirmation": "short",
            "email": "temp1@test.com",
        }
        with app.app_context():
            with pytest.raises(
                ValueError, match="Le mot de passe ne respècte pas les critères"
            ):
                user_manager.create_temp_user(data)

    def test_create_temp_user_success(self, app, applications):
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
            result = user_manager.create_temp_user(data)
        assert "token" in result

        # Ensure user is persisted
        tu = db.session.scalar(
            sa.select(TempUser).where(TempUser.identifiant == "temp2")
        )
        assert tu is not None
        assert tu.token_role == result["token"]


class TestValidTempUser:
    def test_valid_temp_user_no_user(self, app):
        """Should raise when token doesn't match any TempUser"""
        with pytest.raises(
            user_manager.PrintableValueError,
            match="Il n'y a pas d'utilisateur temporaire",
        ):
            user_manager.valid_temp_user({"token": "badtoken", "id_application": 1})

    def test_valid_temp_user_success(self, app, temp_user_fixture, applications):
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

        result = user_manager.valid_temp_user(
            {
                "token": temp_user_fixture.token_role,
                "id_application": applications["app1"].id_application,
            }
        )

        assert "identifiant" in result
        assert result["identifiant"] == temp_user_fixture.identifiant

        # TempUser should be deleted
        tu = db.session.scalar(
            sa.select(TempUser).where(
                TempUser.token_role == temp_user_fixture.token_role
            )
        )
        assert tu is None


class TestChangePassword:
    @staticmethod
    def setup_method(self):
        user_manager.init_user_manager(0, False, False, False)

    def test_change_password_missing_token(self, app):
        with pytest.raises(user_manager.PrintableValueError, match="Token non défini"):
            user_manager.change_password(None, "a", "a")

    def test_change_password_missing_password(self, app):
        with pytest.raises(
            user_manager.PrintableValueError, match="Password non défini"
        ):
            user_manager.change_password("tok", None, None)

    def test_change_password_invalid_password(self, app):
        """Should raise when the provided password does not meet criteria."""
        user_manager.init_user_manager(
            8, True, True, True
        )  # Enforce strong password rules
        with pytest.raises(
            user_manager.PrintableValueError,
            match="Le mot de passe ne respècte pas les critères",
        ):
            user_manager.change_password("valid_token", "weak", "weak")

    def test_change_password_token_not_found(self, app):
        with pytest.raises(
            user_manager.PrintableValueError, match="Pas d'id role associée"
        ):
            user_manager.change_password("invalid", "pw", "pw")

    def test_change_password_success(self, app, group_and_users):
        """Valid case: updates password and deletes token"""
        user = group_and_users["user1"]
        token = "tok123"
        # Clean any existing tokens for this user to avoid duplicates
        db.session.query(CorRoleToken).filter_by(id_role=user.id_role).delete()
        db.session.flush()
        db.session.add(CorRoleToken(id_role=user.id_role, token=token))
        db.session.flush()
        result = user_manager.change_password(token, "newpw", "newpw")
        assert result["identifiant"] == user.identifiant
        # Ensure CorRoleToken deleted
        cors = db.session.scalars(
            sa.select(CorRoleToken).where(CorRoleToken.token == token)
        ).first()
        assert cors is None


class TestPasswordCriterium:
    def test_length_criterion_met(self):
        """Test that password meets minimum length criterion."""
        user_manager.init_user_manager(
            min_password_length=5,
            require_special_character=False,
            require_digit=False,
            require_multiple_case=False,
        )
        assert user_manager._check_password_criteria("12345") is True

    def test_length_criterion_not_met(self):
        """Test that password fails minimum length criterion."""
        user_manager.init_user_manager(
            min_password_length=5,
            require_special_character=False,
            require_digit=False,
            require_multiple_case=False,
        )
        assert user_manager._check_password_criteria("1234") is False

    def test_special_character_required_met(self):
        """Test that password meets special character requirement."""
        user_manager.init_user_manager(
            min_password_length=0,
            require_special_character=True,
            require_digit=False,
            require_multiple_case=False,
        )
        assert user_manager._check_password_criteria("password!") is True

    def test_special_character_required_not_met(self):
        """Test that password fails special character requirement."""
        user_manager.init_user_manager(
            min_password_length=0,
            require_special_character=True,
            require_digit=False,
            require_multiple_case=False,
        )
        assert user_manager._check_password_criteria("password") is False

    def test_digit_required_met(self):
        """Test that password meets digit requirement."""
        user_manager.init_user_manager(
            min_password_length=0,
            require_special_character=False,
            require_digit=True,
            require_multiple_case=False,
        )
        assert user_manager._check_password_criteria("password1") is True

    def test_digit_required_not_met(self):
        """Test that password fails digit requirement."""
        user_manager.init_user_manager(
            min_password_length=0,
            require_special_character=False,
            require_digit=True,
            require_multiple_case=False,
        )
        assert user_manager._check_password_criteria("password") is False

    def test_mixed_case_required_met(self):
        """Test that password meets mixed case requirement."""
        user_manager.init_user_manager(
            min_password_length=0,
            require_special_character=False,
            require_digit=False,
            require_multiple_case=True,
        )
        assert user_manager._check_password_criteria("PassWord") is True

    def test_mixed_case_required_not_met(self):
        """Test that password fails mixed case requirement."""
        user_manager.init_user_manager(
            min_password_length=0,
            require_special_character=False,
            require_digit=False,
            require_multiple_case=True,
        )
        assert user_manager._check_password_criteria("password") is False
        assert user_manager._check_password_criteria("PASSWORD") is False

    def test_all_criterions_met(self):
        """Test that password meets all enabled criterions."""
        user_manager.init_user_manager(
            min_password_length=8,
            require_special_character=True,
            require_digit=True,
            require_multiple_case=True,
        )
        assert user_manager._check_password_criteria("P@ssw0rd") is True

    def test_one_criterion_not_met(self):
        """Test a failure when one of the enabled criterions is not met."""
        user_manager.init_user_manager(
            min_password_length=8,
            require_special_character=True,
            require_digit=True,
            require_multiple_case=True,
        )
        # Shorter than minimum length
        assert user_manager._check_password_criteria("P@sw0r") is False
        # No special character
        assert user_manager._check_password_criteria("Passw0rd") is False
        # No digit
        assert user_manager._check_password_criteria("P@ssword") is False
        # No uppercase letter
        assert user_manager._check_password_criteria("p@ssw0rd") is False
        # No lowercase letter
        assert user_manager._check_password_criteria("P@SSW0RD") is False


class TestRaiseOnPasswordNotMatchingCriterium:
    def test_password_valid(self):
        """Should not raise an exception for a valid password."""
        user_manager.init_user_manager(8, True, True, True)
        valid_password = "P@ssw0rd"
        try:
            user_manager._raise_on_password_not_matching_criteria(valid_password)
        except user_manager.PrintableValueError:
            pytest.fail("Valid password raised an exception.")

    def test_password_invalid(self):
        """Should raise an exception for an invalid password."""
        user_manager.init_user_manager(8, True, True, True)
        invalid_password = "password"  # No special characters, uppercase, or digits
        with pytest.raises(
            user_manager.PrintableValueError,
            match="Le mot de passe ne respècte pas les critères",
        ):
            user_manager._raise_on_password_not_matching_criteria(invalid_password)
