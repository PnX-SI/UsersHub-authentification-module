SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@localhost/postgres"
CODE_APPLICATION = "APPLI_1"
PASS_METHOD = "hash"
SECRET_KEY = "151VD61V6DF1V6F"
COOKIE_EXPIRATION = 3600

AUTHENTICATION = {
    "PROVIDERS": [
        {
            "module": "pypnusershub.auth.providers.default.DefaultConfiguration",
            "id_provider": "local_provider",
        },
        {
            "module": "pypnusershub.auth.providers.cas_inpn_provider.AuthenficationCASINPN",
            "id_provider": "cas_inpn",
            "WS_ID": "bidule",
            "WS_PASSWORD": "bidule",
        },
        {
            "module": "pypnusershub.auth.providers.openid_provider.OpenIDProvider",
            "id_provider": "keycloak",
            "label": "bidule",
            "ISSUER": "bidule",
            "CLIENT_ID": "bidule",
            "CLIENT_SECRET": "bidule",
        },
        {
            "module": "pypnusershub.auth.providers.openid_provider.OpenIDConnectProvider",
            "id_provider": "bis",
            "label": "bidule",
            "ISSUER": "bidule",
            "CLIENT_ID": "bidule",
            "CLIENT_SECRET": "bidule",
        },
        {
            "module": "pypnusershub.auth.providers.usershub_provider.ExternalUsersHubAuthProvider",
            "id_provider": "bis",
            "label": "bidule",
            "login_url": "bidule",
            "logout_url": "bidule",
        },
    ]
}
