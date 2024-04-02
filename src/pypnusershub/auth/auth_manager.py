from .authentication import Authentication, DefaultConfiguration


class AuthManager:
    """
    Manages authentication providers.
    """

    def __init__(self) -> None:
        """
        Initializes the AuthManager instance.
        """
        self.provider_authentication_cls = {"default": DefaultConfiguration()}

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

    def add_provider(self, provider_authentification: Authentication) -> None:
        """
        Registers a new authentication provider.

        Parameters
        ----------
        provider : Authentification
            The authentication provider class.

        Returns
        -------
        None

        Raises
        ------
        AssertionError
            If the provider is not an instance of Authentification.
        """
        if not isinstance(provider_authentification, Authentication):
            raise AssertionError("Provider must be an instance of Authentification")
        self.provider_authentication_cls[provider_authentification.id_provider] = (
            provider_authentification
        )

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

    def get_provider(self, provider_name: str) -> Authentication:
        """
        Returns the current authentication provider.

        Returns
        -------
        Authentification
            The current authentication provider.
        """
        return self.provider_authentication_cls[provider_name]


auth_manager = AuthManager()
