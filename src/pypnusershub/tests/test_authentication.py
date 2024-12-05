import pytest

from flask import Flask

from pypnusershub.auth.auth_manager import AuthManager
from pypnusershub.auth.providers.openid_provider import OpenIDProvider
from pypnusershub.tests.fixtures import *


class TestAuthManager:
    def test_init(self):
        auth_manager = AuthManager()
        assert hasattr(auth_manager, "provider_authentication_cls")
        assert type(auth_manager.provider_authentication_cls) is dict

    def test_add_provider(self, app):
        auth_manager = AuthManager()
        with app.app_context():
            auth_manager.add_provider("test", OpenIDProvider())
            assert "test" in auth_manager

            with pytest.raises(Exception):
                auth_manager.add_provider("test", OpenIDProvider())

    def test_init_app(self, provider_config):
        app = Flask(__name__)

        auth_manager = AuthManager()
        auth_manager.init_app(app, "/authent", [provider_config])

        assert isinstance(app.auth_manager, AuthManager)
        assert "bis" in auth_manager

        provider = auth_manager.get_provider("bis")
        assert provider.group_claim_name == "provided_groups"
        assert provider.group_mapping == {"group1": 1, "group2": 2}
