import json
import threading
import time
from unittest.mock import patch, Mock

import pytest
from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey, ECKey, OKPKey
from marshmallow import ValidationError
from werkzeug.exceptions import InternalServerError, NotFound, Unauthorized

from pypnusershub.auth.providers.openid_token_exchange_provider import (
    OpenIDTokenExchangeProvider,
)
from pypnusershub.env import db
from pypnusershub.db.models import User, UserApplicationRight
from .fixtures import *

ISSUER = "https://login.microsoftonline.com/test-tenant/v2.0"
AUDIENCE = "test-audience-guid"

REQUESTS_GET = "pypnusershub.auth.providers.openid_token_exchange_provider.requests.get"


def mocked_jwks_response(jwks):
    # is_redirect=False: an unconfigured Mock attribute is truthy by default.
    # iter_content side_effect (not return_value): a fresh iterator per call.
    body = json.dumps(jwks).encode()
    return Mock(
        status_code=200,
        is_redirect=False,
        iter_content=Mock(
            side_effect=lambda chunk_size=1: iter([bytes([b]) for b in body])
        ),
        raise_for_status=Mock(),
        close=Mock(),
    )


@pytest.fixture(scope="module")
def rsa_keypair():
    key = RSAKey.generate_key(2048, parameters={"kid": "kid-1"}, private=True)
    jwks = {"keys": [key.as_dict(private=False)]}
    return key, jwks


@pytest.fixture(scope="module")
def other_rsa_keypair():
    """A second, unrelated key: simulates the IdP having rotated its keys."""
    key = RSAKey.generate_key(2048, parameters={"kid": "kid-2"}, private=True)
    jwks = {"keys": [key.as_dict(private=False)]}
    return key, jwks


@pytest.fixture(scope="module")
def ec_keypair():
    """Not every IdP signs with RS256 - this provider is meant to be
    generic, not Entra-specific."""
    key = ECKey.generate_key("P-256", parameters={"kid": "kid-ec"}, private=True)
    jwks = {"keys": [key.as_dict(private=False)]}
    return key, jwks


def make_token(key, alg="RS256", **claim_overrides):
    header = {"alg": alg, "kid": key.as_dict(private=False)["kid"]}
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": int(time.time()) + 3600,
        "unique_name": "test.user",
    }
    payload.update(claim_overrides)
    payload = {k: v for k, v in payload.items() if v is not None}
    return jwt.encode(header, payload, key)


def make_provider(jwks, seed_cache=True, **config_overrides):
    """Configures a provider and, by default, pre-seeds its JWKS cache as
    fresh, so tests don't need to mock requests.get. A test exercising a
    real refresh backdates last_attempt itself."""
    provider = OpenIDTokenExchangeProvider()
    config = {
        "module": "pypnusershub.auth.providers.openid_token_exchange_provider.OpenIDTokenExchangeProvider",
        "id_provider": "test_exchange",
        "JWKS_URL": "https://idp.example/keys",
        "TRUSTED_ISSUERS": [{"ISSUER": ISSUER, "AUDIENCES": [AUDIENCE]}],
        "RECONCILIATE_ATTR": "identifiant",
    }
    config.update(config_overrides)
    provider.configure(config)  # never fetches JWKS itself
    if seed_cache:
        now = time.monotonic()  # the provider's own cache clock
        provider._jwks_cache = {
            "keyset": KeySet.import_key_set(jwks),
            "last_attempt": now,
            "last_success": now,
        }
    return provider


def base_config(**overrides):
    config = {
        "module": "pypnusershub.auth.providers.openid_token_exchange_provider.OpenIDTokenExchangeProvider",
        "id_provider": "test_exchange",
        "JWKS_URL": "https://idp.example/keys",
        "TRUSTED_ISSUERS": [{"ISSUER": ISSUER, "AUDIENCES": [AUDIENCE]}],
    }
    config.update(overrides)
    return config


@pytest.fixture()
def provider(app, rsa_keypair):
    _, jwks = rsa_keypair
    return make_provider(jwks)


@pytest.fixture()
def existing_user(app, applications, profils):
    with db.session.begin_nested():
        user = User(groupe=False, identifiant="test.user")
        db.session.add(user)
        db.session.flush()
        db.session.add(
            UserApplicationRight(
                id_role=user.id_role,
                id_profil=profils["reader"].id_profil,
                id_application=applications["app1"].id_application,
            )
        )
    return user


@pytest.fixture()
def existing_group_with_app_rights(app, applications, profils):
    with db.session.begin_nested():
        group = User(groupe=True, identifiant="test.user")
        db.session.add(group)
        db.session.flush()
        db.session.add(
            UserApplicationRight(
                id_role=group.id_role,
                id_profil=profils["reader"].id_profil,
                id_application=applications["app1"].id_application,
            )
        )
    return group


@pytest.fixture()
def existing_user_without_app_rights(app):
    with db.session.begin_nested():
        user = User(groupe=False, identifiant="test.user.no_rights")
        db.session.add(user)
    return user


@pytest.fixture()
def existing_disabled_user(app, applications, profils):
    with db.session.begin_nested():
        user = User(groupe=False, identifiant="test.user.disabled", active=False)
        db.session.add(user)
        db.session.flush()
        db.session.add(
            UserApplicationRight(
                id_role=user.id_role,
                id_profil=profils["reader"].id_profil,
                id_application=applications["app1"].id_application,
            )
        )
    return user


# --- Configuration validation ---------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"JWKS_URL": "http://idp.example/keys"},
        {"TRUSTED_ISSUERS": [{"ISSUER": "", "AUDIENCES": [AUDIENCE]}]},
        {"TRUSTED_ISSUERS": [{"ISSUER": ISSUER, "AUDIENCES": []}]},
        {"TRUSTED_ISSUERS": []},
        {"RECONCILIATE_ATTR": "not_a_real_column"},
        {"RECONCILIATE_ATTR": "check_password"},  # a real method, not a column
        {"JWKS_MAX_AGE": 0},
        {"JWKS_TIMEOUT": 0},
        {"JWKS_TIMEOUT": 2.5},  # strict=True: floats aren't silently truncated
        {"JWKS_DEBOUNCE": 0},
        {"TOKEN_HEADER_NAME": ""},
        {"IDENTIFIER_CLAIMS": []},
        {"IDENTIFIER_CLAIMS": [""]},
        {"ALGORITHMS": []},
        {"ALGORITHMS": ["none"]},  # joserfc only warns about "none", doesn't refuse it
        {"ALGORITHMS": ["HS256"]},
        {"UNKNOWN_USER_STATUS_CODE": 200},
    ],
    ids=[
        "non-https-jwks-url",
        "empty-issuer",
        "empty-audiences",
        "empty-trusted-issuers",
        "unknown-reconciliate-attr",
        "reconciliate-attr-not-a-column",
        "zero-jwks-max-age",
        "zero-jwks-timeout",
        "non-integer-jwks-timeout",
        "zero-jwks-debounce",
        "empty-token-header-name",
        "empty-identifier-claims",
        "empty-identifier-claim-element",
        "empty-algorithms",
        "none-algorithm",
        "unsupported-algorithm",
        "out-of-range-status-code",
    ],
)
def test_configure_rejects_invalid_config(app, overrides):
    with pytest.raises(ValidationError):
        OpenIDTokenExchangeProvider().configure(base_config(**overrides))


def test_two_trusted_issuer_pairs(app, rsa_keypair, existing_user):
    """Two (issuer, audiences) pairs configured, a token matching either is accepted."""
    key, jwks = rsa_keypair
    other_issuer = "https://sts.windows.net/test-tenant/"
    other_audience = "v1-app-id-uri"
    provider = make_provider(
        jwks,
        TRUSTED_ISSUERS=[
            {"ISSUER": ISSUER, "AUDIENCES": [AUDIENCE]},
            {"ISSUER": other_issuer, "AUDIENCES": [other_audience]},
        ],
    )
    token = make_token(key, iss=other_issuer, aud=other_audience)
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        user = provider.authenticate()
    assert user.identifiant == "test.user"


def test_issuer_audience_cross_match(app, rsa_keypair):
    """iss from one pair + aud from another must not validate."""
    key, jwks = rsa_keypair
    other_issuer = "https://sts.windows.net/test-tenant/"
    other_audience = "v1-app-id-uri"
    provider = make_provider(
        jwks,
        TRUSTED_ISSUERS=[
            {"ISSUER": ISSUER, "AUDIENCES": [AUDIENCE]},
            {"ISSUER": other_issuer, "AUDIENCES": [other_audience]},
        ],
    )
    # iss from the v2 pair, aud from the v1 pair: neither pair matches both.
    token = make_token(key, iss=ISSUER, aud=other_audience)
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized):
            provider.authenticate()


def test_authorize_not_implemented(provider):
    with pytest.raises(NotFound):
        provider.authorize()


# --- Token validation -------------------------------------------------------


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "   "}], ids=["missing", "blank"]
)
def test_blank_header(app, provider, headers):
    with app.test_request_context(headers=headers):
        with pytest.raises(Unauthorized):
            provider.authenticate()


def test_missing_bearer_prefix(app, provider, rsa_keypair, existing_user):
    token = make_token(rsa_keypair[0])
    with app.test_request_context(headers={"Authorization": token}):
        user = provider.authenticate()
    assert user.identifiant == "test.user"


def test_aud_as_a_list(app, provider, rsa_keypair, existing_user):
    # RFC 7519: a token may legally carry several audiences in "aud".
    token = make_token(rsa_keypair[0], aud=[AUDIENCE, "some-other-audience"])
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        user = provider.authenticate()
    assert user.identifiant == "test.user"


@pytest.mark.parametrize(
    "claim_overrides",
    [
        {"iss": "https://not-the-right-issuer"},
        {"aud": "some-other-audience"},
        {"exp": None},
        {"unique_name": None},
    ],
    ids=["wrong-issuer", "wrong-audience", "missing-exp", "no-identifier-claim"],
)
def test_authenticate_rejects_invalid_token(
    app, provider, rsa_keypair, claim_overrides
):
    token = make_token(rsa_keypair[0], **claim_overrides)
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized):
            provider.authenticate()


def test_expired_token(app, provider, rsa_keypair):
    token = make_token(rsa_keypair[0], exp=int(time.time()) - 3600)
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized) as exc_info:
            provider.authenticate()
    # Never leak which specific check failed.
    assert "exp" not in str(exc_info.value.description).lower()


def test_identifier_claims_order(app, provider, rsa_keypair, existing_user):
    provider.identifier_claims = ["upn", "preferred_username"]
    token = make_token(rsa_keypair[0], unique_name=None, preferred_username="test.user")
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        user = provider.authenticate()
    assert user.identifiant == "test.user"


def test_malformed_token_no_refetch(app, provider):
    # Backdated so the debounce alone can't hide a wrongly-triggered retry.
    provider._jwks_cache["last_attempt"] = time.monotonic() - 3600
    with patch(REQUESTS_GET) as mocked_get:
        with app.test_request_context(headers={"Authorization": "Bearer not.a.jwt"}):
            with pytest.raises(Unauthorized):
                provider.authenticate()
        mocked_get.assert_not_called()


def test_authenticate_custom_token_header_name(app, rsa_keypair, existing_user):
    key, jwks = rsa_keypair
    provider = make_provider(jwks, TOKEN_HEADER_NAME="X-Idp-Token")
    token = make_token(key)
    with app.test_request_context(headers={"X-Idp-Token": f"Bearer {token}"}):
        user = provider.authenticate()
    assert user.identifiant == "test.user"


@pytest.mark.parametrize(
    "algorithms, should_succeed",
    [(["ES256"], True), (["RS256"], False)],
    ids=["allowed", "not-allowed"],
)
def test_authenticate_es256_support(
    app, ec_keypair, existing_user, algorithms, should_succeed
):
    # The provider isn't Entra-specific: ES256 must work with a config
    # change, and never get accepted just because the default is RS256.
    key, jwks = ec_keypair
    provider = make_provider(jwks, ALGORITHMS=algorithms)
    token = make_token(key, alg="ES256")
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        if should_succeed:
            assert provider.authenticate().identifiant == "test.user"
        else:
            with pytest.raises(Unauthorized):
                provider.authenticate()


def test_ed25519_support(app, existing_user):
    key = OKPKey.generate_key("Ed25519", parameters={"kid": "ed-1"}, private=True)
    jwks = {"keys": [key.as_dict(private=False)]}
    provider = make_provider(jwks, ALGORITHMS=["Ed25519"])
    header = {"alg": "Ed25519", "kid": "ed-1"}
    payload = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": int(time.time()) + 3600,
        "unique_name": "test.user",
    }
    token = jwt.encode(header, payload, key, algorithms=["Ed25519"])
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        user = provider.authenticate()
    assert user.identifiant == "test.user"


@pytest.mark.parametrize(
    "client_id, should_succeed",
    [("expected-client-id", True), ("some-other-client-id", False)],
    ids=["known-client", "unknown-client"],
)
def test_authenticate_allowed_clients(
    app, rsa_keypair, existing_user, client_id, should_succeed
):
    key, jwks = rsa_keypair
    provider = make_provider(jwks, ALLOWED_CLIENTS=["expected-client-id"])
    token = make_token(key, azp=client_id)
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        if should_succeed:
            assert provider.authenticate().identifiant == "test.user"
        else:
            with pytest.raises(Unauthorized):
                provider.authenticate()


@pytest.mark.parametrize(
    "scp, should_succeed",
    [(None, False), ("user_impersonation", True)],
    ids=["missing", "present"],
)
def test_authenticate_required_claims(
    app, rsa_keypair, existing_user, scp, should_succeed
):
    # Guards against an ID token (no authorization claim) being accepted in
    # place of an access token for the same app registration.
    key, jwks = rsa_keypair
    provider = make_provider(jwks, REQUIRED_CLAIMS=["scp", "roles"])
    token = make_token(key, scp=scp)
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        if should_succeed:
            assert provider.authenticate().identifiant == "test.user"
        else:
            with pytest.raises(Unauthorized):
                provider.authenticate()


# --- Reconciliation ----------------------------------------------------------


def test_unknown_user_status_code(app, rsa_keypair):
    key, jwks = rsa_keypair
    provider = make_provider(jwks, UNKNOWN_USER_STATUS_CODE=490)
    token = make_token(key, unique_name="no.such.user")
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized) as exc_info:
            provider.authenticate()
    assert exc_info.value.code == 490
    # The identifier that was looked up must never reach the client.
    assert "no.such.user" not in str(exc_info.value.description)


def test_user_without_app_rights(
    app, provider, rsa_keypair, existing_user_without_app_rights
):
    token = make_token(rsa_keypair[0], unique_name="test.user.no_rights")
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized):
            provider.authenticate()


def test_group_matching_identifiant(
    app, provider, rsa_keypair, existing_group_with_app_rights
):
    token = make_token(rsa_keypair[0])  # unique_name "test.user", matches the group
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized):
            provider.authenticate()


def test_disabled_user(app, provider, rsa_keypair, existing_disabled_user):
    token = make_token(rsa_keypair[0], unique_name="test.user.disabled")
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized):
            provider.authenticate()


def test_duplicate_email_reconciliation(app, rsa_keypair, applications, profils):
    key, jwks = rsa_keypair
    with db.session.begin_nested():
        for _ in range(2):
            user = User(
                groupe=False, identifiant=f"user-{_}", email="shared@example.com"
            )
            db.session.add(user)
            db.session.flush()
            db.session.add(
                UserApplicationRight(
                    id_role=user.id_role,
                    id_profil=profils["reader"].id_profil,
                    id_application=applications["app1"].id_application,
                )
            )
    provider = make_provider(jwks, RECONCILIATE_ATTR="email")
    token = make_token(key, unique_name="shared@example.com")
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized):  # not MultipleResultsFound / 500
            provider.authenticate()


def test_malformed_uuid_role(app, rsa_keypair):
    key, jwks = rsa_keypair
    provider = make_provider(jwks, RECONCILIATE_ATTR="uuid_role")
    token = make_token(key, unique_name="not-a-valid-uuid")
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized):  # not DataError / 500
            provider.authenticate()


def test_non_string_identifier_claim(app, provider, rsa_keypair):
    # A claim value that isn't a string (e.g. a number) would otherwise be
    # compared directly against a SQL text column - a database-level error,
    # not a clean "invalid token" response.
    token = make_token(rsa_keypair[0], unique_name=123456)
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized):  # not a 500
            provider.authenticate()


def test_nul_byte_in_identifier_claim(app, provider, rsa_keypair):
    # psycopg2 rejects a NUL byte with a plain ValueError, not a DataError -
    # it must be caught before reaching the database, not just after.
    token = make_token(rsa_keypair[0], unique_name="test.user\x00")
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        with pytest.raises(Unauthorized):  # not a 500
            provider.authenticate()


def test_dataerror_uses_savepoint(app, rsa_keypair):
    """Recovery must go through the begin_nested() SAVEPOINT, not a blanket
    rollback() - checked directly since pytest's TestSession makes
    rollback() SAVEPOINT-scoped anyway, masking the difference."""
    key, jwks = rsa_keypair
    provider = make_provider(jwks, RECONCILIATE_ATTR="uuid_role")
    token = make_token(key, unique_name="not-a-valid-uuid")
    with patch.object(
        db.session, "rollback", wraps=db.session.rollback
    ) as mocked_rollback:
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(Unauthorized):
                provider.authenticate()
        mocked_rollback.assert_not_called()


# --- JWKS fetching, caching and key rotation --------------------------------


def test_valid_token(app, provider, rsa_keypair, existing_user):
    token = make_token(rsa_keypair[0])
    with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
        user = provider.authenticate()
    assert user.identifiant == "test.user"


def test_key_rotation_retry_succeeds(app, provider, other_rsa_keypair, existing_user):
    # Token signed with a not-yet-cached key triggers the refresh-and-retry
    # path; backdated so the debounce lets the retry actually hit the network.
    provider._jwks_cache["last_attempt"] = time.monotonic() - 3600
    new_key, new_jwks = other_rsa_keypair
    token = make_token(new_key)
    with patch(REQUESTS_GET, return_value=mocked_jwks_response(new_jwks)) as mocked_get:
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            user = provider.authenticate()
        assert mocked_get.called  # the stale cache forced one real refresh
    assert user.identifiant == "test.user"


def test_key_rotation_retry_idp_unreachable(app, provider, other_rsa_keypair):
    """IdP unreachable during the retry, but a cache exists: falls back to
    the stale keys and rejects as invalid, not a 500."""
    provider._jwks_cache["last_attempt"] = time.monotonic() - 3600
    new_key, _ = other_rsa_keypair
    token = make_token(new_key)  # signed with a key not in the cache
    with patch(REQUESTS_GET, side_effect=Exception("connection refused")):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(Unauthorized):
                provider.authenticate()


def test_jwks_http_error_no_cache(app, rsa_keypair):
    provider = make_provider(rsa_keypair[1], seed_cache=False)
    token = make_token(rsa_keypair[0])
    with patch(REQUESTS_GET, side_effect=Exception("connection refused")):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(InternalServerError):
                provider.authenticate()


def test_jwks_malformed_response_recovers(app, rsa_keypair):
    """A 200 with a body that isn't an actual JWKS must be treated as a
    failed fetch, not cached - otherwise it locks out every login until
    a restart."""
    provider = make_provider(rsa_keypair[1], seed_cache=False)
    token = make_token(rsa_keypair[0])
    with patch(REQUESTS_GET, return_value=mocked_jwks_response({"error": "nope"})):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(InternalServerError):
                provider.authenticate()
    # No permanent damage: once the IdP serves a real JWKS, login works.
    provider._jwks_cache["last_attempt"] = time.monotonic() - 3600
    _, good_jwks = rsa_keypair
    with patch(REQUESTS_GET, return_value=mocked_jwks_response(good_jwks)):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(Unauthorized):  # no matching user seeded here
                provider.authenticate()


def test_jwks_outage_debounce(app, rsa_keypair):
    """The debounce must apply even with no prior successful fetch."""
    provider = make_provider(rsa_keypair[1], seed_cache=False)
    token = make_token(rsa_keypair[0])
    with patch(REQUESTS_GET, side_effect=Exception("connection refused")) as mocked_get:
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(InternalServerError):
                provider.authenticate()
            assert mocked_get.call_count == 1
            with pytest.raises(InternalServerError):
                provider.authenticate()
            # Second call within the debounce window: no new HTTP attempt.
            assert mocked_get.call_count == 1


def test_jwks_max_age_refresh(app, rsa_keypair):
    """A revoked key must stop being trusted even without a decode failure."""
    key, jwks = rsa_keypair
    provider = make_provider(jwks, JWKS_MAX_AGE=1)
    provider._jwks_cache["last_success"] = time.monotonic() - 3600
    provider._jwks_cache["last_attempt"] = time.monotonic() - 3600
    token = make_token(key)
    with patch(REQUESTS_GET, return_value=mocked_jwks_response(jwks)) as mocked_get:
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(Unauthorized):  # no matching user seeded here
                provider.authenticate()
    assert mocked_get.called  # refreshed despite no decode failure


def test_jwks_redirect_response(app, rsa_keypair):
    """requests follows redirects by default; allow_redirects=False must stop
    an https->http downgrade via a 302."""
    provider = make_provider(rsa_keypair[1], seed_cache=False)
    token = make_token(rsa_keypair[0])
    redirect_response = Mock(
        status_code=302,
        is_redirect=True,
        headers={"Location": "http://evil.example/keys"},
    )
    with patch(REQUESTS_GET, return_value=redirect_response):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(InternalServerError):
                provider.authenticate()


def test_jwks_slow_drip_timeout(app, rsa_keypair):
    """requests' timeout= bounds silence between reads, not total duration -
    a steady drip, each chunk within that per-read timeout, must still be
    bounded by JWKS_TIMEOUT overall."""
    key, jwks = rsa_keypair
    provider = make_provider(jwks, seed_cache=False, JWKS_TIMEOUT=1)
    body = json.dumps(jwks).encode()

    def dripping_iter_content(chunk_size=1):
        for byte in body:
            time.sleep(0.05)
            yield bytes([byte])

    slow_response = Mock(
        status_code=200,
        is_redirect=False,
        iter_content=Mock(side_effect=dripping_iter_content),
        raise_for_status=Mock(),
        close=Mock(),
    )
    token = make_token(key)
    with patch(REQUESTS_GET, return_value=slow_response):
        start = time.monotonic()
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(InternalServerError):
                provider.authenticate()
        elapsed = time.monotonic() - start
    assert elapsed < 3  # bounded by JWKS_TIMEOUT, not the drip's full duration


def test_jwks_oversized_response(app, rsa_keypair):
    """Pads an otherwise-valid JWKS past the limit, so the size cap itself
    is what causes the rejection, not json.loads() choking on garbage."""
    key, jwks = rsa_keypair
    provider = make_provider(jwks, seed_cache=False)
    oversized_jwks = {**jwks, "padding": "x" * (provider._MAX_JWKS_BYTES + 1)}
    body = json.dumps(oversized_jwks).encode()
    oversized_response = Mock(
        status_code=200,
        is_redirect=False,
        iter_content=Mock(side_effect=lambda chunk_size=1: (bytes([b]) for b in body)),
        raise_for_status=Mock(),
        close=Mock(),
    )
    token = make_token(key)
    with patch(REQUESTS_GET, return_value=oversized_response):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(InternalServerError):
                provider.authenticate()


def test_jwks_oversized_response_stops_early(app, rsa_keypair):
    """Must stop reading as soon as the cap is exceeded, not after consuming
    everything on offer. The generator is large but finite, so a regression
    fails loudly instead of hanging the test."""
    key, jwks = rsa_keypair
    provider = make_provider(jwks, seed_cache=False)
    bytes_consumed = 0
    far_more_than_the_cap = provider._MAX_JWKS_BYTES * 10

    def oversized_iter_content(chunk_size=1):
        nonlocal bytes_consumed
        for _ in range(far_more_than_the_cap):
            bytes_consumed += 1
            yield b"x"
        raise AssertionError("consumed far more than the size cap should allow")

    oversized_response = Mock(
        status_code=200,
        is_redirect=False,
        iter_content=Mock(side_effect=oversized_iter_content),
        raise_for_status=Mock(),
        close=Mock(),
    )
    token = make_token(key)
    with patch(REQUESTS_GET, return_value=oversized_response):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            with pytest.raises(InternalServerError):
                provider.authenticate()
    # Stopped right at the cap, not after consuming everything on offer.
    assert provider._MAX_JWKS_BYTES < bytes_consumed < provider._MAX_JWKS_BYTES + 100


def test_jwks_one_unusable_key(app, rsa_keypair, existing_user):
    """An IdP can list a key type we don't support alongside a usable one -
    _import_jwks must import what it can rather than reject the whole set."""
    key, jwks = rsa_keypair
    mixed_jwks = {"keys": [{"kty": "AKP", "alg": "ML-DSA-44"}, *jwks["keys"]]}
    provider = make_provider(jwks, seed_cache=False)
    token = make_token(key)
    with patch(REQUESTS_GET, return_value=mocked_jwks_response(mixed_jwks)):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            user = provider.authenticate()
    assert user.identifiant == "test.user"


def test_jwks_non_object_key_entries(app, rsa_keypair, existing_user):
    """A non-object key entry must be skipped, not invalidate the whole set."""
    key, jwks = rsa_keypair
    malformed_jwks = {"keys": [None, "not-an-object", *jwks["keys"]]}
    provider = make_provider(jwks, seed_cache=False)
    token = make_token(key)
    with patch(REQUESTS_GET, return_value=mocked_jwks_response(malformed_jwks)):
        with app.test_request_context(headers={"Authorization": f"Bearer {token}"}):
            user = provider.authenticate()
    assert user.identifiant == "test.user"


def test_jwks_debounce_slow_failure(app, rsa_keypair):
    """last_attempt must be recorded at the end of an attempt, not the
    start, or a slow failure dodges the debounce on the very next request."""
    provider = make_provider(rsa_keypair[1], seed_cache=False, JWKS_DEBOUNCE=1)

    def slow_failure(*args, **kwargs):
        time.sleep(0.2)
        raise Exception("connection timed out")

    with patch(REQUESTS_GET, side_effect=slow_failure) as mocked_get:
        before = time.monotonic()
        with pytest.raises(InternalServerError):
            provider._get_jwks()
        after = time.monotonic()
        assert provider._jwks_cache["last_attempt"] >= after - 0.05 > before
        # Immediately after: still well within the 1s debounce.
        with pytest.raises(InternalServerError):
            provider._get_jwks()
    assert mocked_get.call_count == 1


# --- Concurrency -------------------------------------------------------------


def test_jwks_cold_cache_single_fetch(app, rsa_keypair):
    """A cold-cache thundering herd must share one fetch, not each block."""
    key, jwks = rsa_keypair
    provider = make_provider(jwks, seed_cache=False)
    call_count = 0
    count_lock = threading.Lock()

    def slow_fetch(*args, **kwargs):
        nonlocal call_count
        with count_lock:
            call_count += 1
        time.sleep(0.2)
        return mocked_jwks_response(jwks)

    results = []

    def worker():
        try:
            provider._get_jwks()
            results.append("ok")
        except Exception as e:
            results.append(type(e).__name__)

    with patch(REQUESTS_GET, side_effect=slow_fetch):
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert call_count == 1
    assert results == ["ok"] * 5


def test_jwks_warm_cache_non_blocking(app, rsa_keypair):
    """Unlike a cold cache, a usable (if stale) keyset must not be made to
    wait on a slow/stuck refresh. call_count == 1 alone wouldn't prove
    this (a blocking lock gives the same count), so this instead requires
    the other 3 threads to finish *before* the one real fetch is released."""
    key, jwks = rsa_keypair
    provider = make_provider(jwks, JWKS_MAX_AGE=1)
    provider._jwks_cache["last_success"] = time.monotonic() - 3600
    provider._jwks_cache["last_attempt"] = time.monotonic() - 3600

    call_count = 0
    count_lock = threading.Lock()
    fetch_started = threading.Event()
    release_fetch = threading.Event()

    def slow_fetch(*args, **kwargs):
        nonlocal call_count
        with count_lock:
            call_count += 1
        fetch_started.set()
        release_fetch.wait(timeout=5)
        return mocked_jwks_response(jwks)

    results = []
    results_lock = threading.Lock()
    other_three_done = threading.Event()

    def worker():
        keyset = provider._get_jwks()
        with results_lock:
            results.append(keyset)
            if len(results) >= 3:
                other_three_done.set()

    with patch(REQUESTS_GET, side_effect=slow_fetch):
        threads = [threading.Thread(target=worker) for _ in range(4)]
        for thread in threads:
            thread.start()
        try:
            assert fetch_started.wait(timeout=2)  # the one real fetch is under way
            # The other 3 must complete *without* the fetch being released yet.
            assert other_three_done.wait(timeout=2)
        finally:
            release_fetch.set()  # always, even on assertion failure above
        for thread in threads:
            thread.join()

    assert call_count == 1
    assert len(results) == 4


def test_key_rotation_retry_wait_timeout(app, rsa_keypair, other_rsa_keypair):
    """A thread waiting on a refresh that never completes must give up after
    JWKS_TIMEOUT, not block forever."""
    _, jwks = rsa_keypair
    new_key, _ = other_rsa_keypair
    provider = make_provider(jwks, JWKS_TIMEOUT=1)
    provider._jwks_cache["last_attempt"] = time.monotonic() - 3600
    token = make_token(new_key)  # signed with a key not in the cache

    lock_held = threading.Event()

    def never_finishes(*args, **kwargs):
        lock_held.set()
        time.sleep(3)  # well past JWKS_TIMEOUT=1
        raise Exception("should never be reached")

    with patch(REQUESTS_GET, side_effect=never_finishes):
        # Holds _jwks_lock for the whole sleep.
        stuck_refresh = threading.Thread(
            target=lambda: provider._get_jwks(refresh=True), daemon=True
        )
        stuck_refresh.start()
        assert lock_held.wait(timeout=2)

        start = time.monotonic()
        with pytest.raises(Unauthorized):
            provider._validate_token(token)
        elapsed = time.monotonic() - start

    # Bounded by JWKS_TIMEOUT (1s), not by the other thread's 3s hold.
    assert elapsed < 2.5


def test_concurrent_key_rotation_waits_for_refresh(app, rsa_keypair, other_rsa_keypair):
    """A rotation retry must wait for a concurrent refresh rather than reuse
    the already-known-wrong keyset, or legitimate tokens get a spurious 401.
    Exercises _validate_token directly: authenticate() would hit db.session
    from several threads, each with its own scoped session."""
    _, jwks = rsa_keypair
    new_key, new_jwks = other_rsa_keypair
    provider = make_provider(jwks)
    provider._jwks_cache["last_attempt"] = time.monotonic() - 3600
    token = make_token(new_key)  # signed with a key not yet in the cache

    release_fetch = threading.Event()

    def slow_fetch(*args, **kwargs):
        release_fetch.wait(timeout=5)
        return mocked_jwks_response(new_jwks)

    results = []
    results_lock = threading.Lock()

    def worker():
        try:
            claims = provider._validate_token(token)
            outcome = claims.get("unique_name")
        except Unauthorized:
            outcome = "401"
        with results_lock:
            results.append(outcome)

    with patch(REQUESTS_GET, side_effect=slow_fetch):
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for thread in threads:
            thread.start()
        time.sleep(0.2)  # let every thread reach the retry and start waiting
        release_fetch.set()
        for thread in threads:
            thread.join()

    assert results == ["test.user"] * 5
