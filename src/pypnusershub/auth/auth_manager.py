from .authentication import Authentication
from .providers import DefaultConfiguration
import importlib


class AuthManager:
    """
    Manages authentication providers.
    """

    def __init__(self) -> None:
        """
        Initializes the AuthManager instance.
        """
        self.provider_authentication_cls = {}
        self.add_provider("local_provider", DefaultConfiguration())

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
        self, id_instance: str, provider_authentification: Authentication
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

        assert id_instance not in self.provider_authentication_cls
        if not isinstance(provider_authentification, Authentication):
            raise AssertionError("Provider must be an instance of Authentication")
        self.provider_authentication_cls[id_instance] = provider_authentification

    def init_app(self, app, prefix: str = "/auth") -> None:
        """
        Initializes the Flask application with the AuthManager.

        Parameters
        ----------
        app : Flask
            The Flask application instance.

        Returns
        -------
        None
        """
        from pypnusershub.routes import routes

        app.auth_manager = self

        app.register_blueprint(routes, url_prefix=prefix)

        for path_provider in app.config["AUTHENTICATION"].get("PROVIDERS", []):
            import_path, class_name = (
                ".".join(path_provider.split(".")[:-1]),
                path_provider.split(".")[-1],
            )
            module = importlib.import_module(import_path)
            class_ = getattr(module, class_name)
            name_, _ = class_.configuration_schema()
            for config in app.config["AUTHENTICATION"]["PROVIDERS_CONFIG"][name_][
                "CONFIG"
            ]:
                instance_provider: Authentication = class_()
                with app.app_context():
                    instance_provider.configure(configuration=config)
                    self.add_provider(instance_provider.label, instance_provider)

    def get_provider(self, instance_name: str) -> Authentication:
        """
        Returns the current authentication provider.

        Returns
        -------
        Authentification
            The current authentication provider.
        """
        return self.provider_authentication_cls[instance_name]

    # Home page of the app using auth_manager
    home_page = ""


auth_manager = AuthManager()
