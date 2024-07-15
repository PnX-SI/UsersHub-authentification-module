import pytest

from flask import Flask

from pypnusershub.auth.auth_manager import AuthManager
from pypnusershub.auth.providers.openid_provider import OpenIDProvider


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

    def test_init_app(self):
        app = Flask(__name__)

        providers = [
            {
                "module": "pypnusershub.auth.providers.openid_provider.OpenIDConnectProvider",
                "id_provider": "bis",
                "label": "bidule",
                "ISSUER": "bidule",
                "CLIENT_ID": "bidule",
                "CLIENT_SECRET": "bidule",
            }
        ]
        auth_manager = AuthManager()
        auth_manager.init_app(app, "/authent", providers)

        assert isinstance(app.auth_manager, AuthManager)
        assert "bis" in auth_manager
