import importlib

import sqlalchemy as sa
from pypnusershub.db.models import Provider
from pypnusershub.env import db

from .authentication import Authentication


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
        if not db.engine.has_table(Provider.__tablename__, schema="utilisateurs"):
            return
        assert id_provider not in self.provider_authentication_cls
        query = sa.exists(Provider).where(Provider.name == id_provider).select()
        if not db.session.scalar(query):
            db.session.add(
                Provider(name=id_provider, url=provider_authentification.login_url)
            )
            db.session.commit()
        if not isinstance(provider_authentification, Authentication):
            raise AssertionError("Provider must be an instance of Authentication")
        self.provider_authentication_cls[id_provider] = provider_authentification

    def init_app(
        self, app, prefix: str = "/auth", providers_declaration: list[ProviderType] = []
    ) -> None:
        """
        Initializes the Flask application with the AuthManager. In addtion, it registers the authentification module blueprint.

        Parameters
        ----------
        app : Flask
            The Flask application instance.

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
