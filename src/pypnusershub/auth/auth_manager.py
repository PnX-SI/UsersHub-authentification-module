import importlib

import sqlalchemy as sa
from pypnusershub.db.models import Provider
from pypnusershub.env import db

from .authentication import Authentication
from pypnusershub.login_manager import login_manager


from typing import TypedDict

ProviderType = TypedDict(
    "Provider",
    {
        "id_provider": str,
        "module": str,
        "label": str,
        "group_mapping": dict,
        "logo": str,
    },
)


class AuthManager:
    """
    Manages authentication providers.
    """

    def __init__(self) -> None:
        """
        Initializes the AuthManager instance.
        """
        self.provider_authentication_cls = {}

    def __contains__(self, item) -> bool:
        """
        Checks if a provider is registered.

        Parameters
        ----------
        item : str
            The provider name.

        Returns
        -------
        bool
            True if the provider is registered, False otherwise.
        """
        return item in self.provider_authentication_cls

    def add_provider(
        self, id_provider: str, provider_authentification: Authentication
    ) -> None:
        """
        Registers a new authentication provider instance.

        Parameters
        ----------
        id_instance : str
            identifier of the new provider instance
        provider : Authentification
            The authentication provider class.

        Raises
        ------
        AssertionError
            If the provider is not an instance of Authentification.
        """
        if not isinstance(provider_authentification, Authentication):
            raise AssertionError("Provider must be an instance of Authentication")
        if id_provider in self.provider_authentication_cls:
            raise Exception(
                f"Id provider {id_provider} already exist, please check your authentication config"
            )
        self.provider_authentication_cls[id_provider] = provider_authentification

    def init_app(
        self, app, prefix: str = "/auth", providers_declaration: list[ProviderType] = []
    ) -> None:
        """
        Initializes the Flask application with the AuthManager. In addition, it registers the authentication module blueprint.

        Parameters
        ----------
        app : Flask
            The Flask application instance.
        prefix : str, optional
            The URL prefix for the authentication module blueprint.
        providers_declaration : list[ProviderType], optional
            List of provider declarations to be used by the AuthManager.

        """
        from pypnusershub.routes import routes

        app.auth_manager = self
        app.register_blueprint(routes, url_prefix=prefix)
        for provider_config in providers_declaration:
            path_provider = provider_config.get("module")
            import_path, class_name = (
                ".".join(path_provider.split(".")[:-1]),
                path_provider.split(".")[-1],
            )
            module = importlib.import_module(import_path)
            class_ = getattr(module, class_name)

            with app.app_context():
                instance_provider: Authentication = class_()
                instance_provider.configure(configuration=provider_config)
                self.add_provider(instance_provider.id_provider, instance_provider)
        login_manager.init_app(app)

    def get_provider(self, instance_name: str) -> Authentication:
        """
        Returns the current authentication provider.

        Returns
        -------
        Authentification
            The current authentication provider.
        """
        return self.provider_authentication_cls[instance_name]


auth_manager = AuthManager()
