import json
import logging
import threading
import time
from typing import Any, Union

import requests
import sqlalchemy as sa
from flask import Response, request
from joserfc import jwt
from joserfc.errors import (
    BadSignatureError,
    ClaimError,
    InvalidKeyIdError,
    MissingKeyError,
)
from joserfc.jwk import KeySet
from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate
from sqlalchemy.exc import DataError, MultipleResultsFound
from werkzeug.exceptions import NotFound, Unauthorized

from pypnusershub.auth import Authentication, ProviderConfigurationSchema
from pypnusershub.db import db, models

log = logging.getLogger(__name__)


# Asymmetric only - the JWKS holds public keys, never a shared secret.
# "none" is never allowed.
_ALLOWED_ALGORITHMS = [
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
    "PS256",
    "PS384",
    "PS512",
    "Ed25519",
    "Ed448",  # not "EdDSA", deprecated by RFC 9864
]


class TrustedIssuerSchema(Schema):
    """One (issuer, audiences) pair - Entra v1 and v2 pair different values
    for both, so they're matched together, not independently."""

    ISSUER = fields.String(required=True, validate=validate.Length(min=1))
    AUDIENCES = fields.List(
        fields.String(validate=validate.Length(min=1)),
        required=True,
        validate=validate.Length(min=1),
    )


class OpenIDTokenExchangeProvider(Authentication):
    """Exchanges a token already obtained client-side (e.g. mobile MSAL) for
    a GeoNature token, without a server-driven redirect flow."""

    logo = ""
    is_external = True
    is_hidden = True
    reconciliate_attr = "email"
    identifier_claims = ["unique_name"]

    def __init__(self):
        self._jwks_cache = {"keyset": None, "last_attempt": None, "last_success": None}
        self._jwks_lock = threading.Lock()

    def configure(self, configuration: Union[dict, Any]) -> None:
        class TokenExchangeConfiguration(ProviderConfigurationSchema):
            # https only; allow_redirects=False below stops a downgrade.
            JWKS_URL = fields.Url(schemes={"https"}, require_tld=False, required=True)
            TRUSTED_ISSUERS = fields.List(
                fields.Nested(TrustedIssuerSchema),
                required=True,
                validate=validate.Length(min=1),
            )
            JWKS_TIMEOUT = fields.Integer(
                load_default=10, validate=validate.Range(min=1), strict=True
            )
            JWKS_DEBOUNCE = fields.Integer(
                load_default=10, validate=validate.Range(min=1), strict=True
            )
            # Periodic refresh even without a decode failure, so a revoked
            # key eventually stops being trusted.
            JWKS_MAX_AGE = fields.Integer(
                load_default=3600, validate=validate.Range(min=1), strict=True
            )
            TOKEN_HEADER_NAME = fields.String(
                load_default="Authorization", validate=validate.Length(min=1)
            )
            ALGORITHMS = fields.List(
                fields.String(validate=validate.OneOf(_ALLOWED_ALGORITHMS)),
                load_default=["RS256"],
                validate=validate.Length(min=1),
            )
            IDENTIFIER_CLAIMS = fields.List(
                fields.String(validate=validate.Length(min=1)),
                load_default=["unique_name"],
                validate=validate.Length(min=1),
            )
            ALLOWED_CLIENTS = fields.List(
                fields.String(validate=validate.Length(min=1)), load_default=[]
            )
            # Distinguishes an access token from an ID token sharing the
            # same iss/aud; no portable claim name across IdPs (e.g.
            # ["scp"] for Entra).
            REQUIRED_CLAIMS = fields.List(
                fields.String(validate=validate.Length(min=1)), load_default=[]
            )
            UNKNOWN_USER_STATUS_CODE = fields.Integer(
                load_default=401,
                validate=validate.Range(min=400, max=599),
                strict=True,
            )

        super().configure(configuration)
        try:
            configuration = TokenExchangeConfiguration().load(
                configuration, unknown=EXCLUDE
            )
        except ValidationError as e:
            raise ValidationError(
                f"Error while loading OpenIDTokenExchangeProvider configuration: {e}"
            )
        self.jwks_url = configuration["JWKS_URL"]
        self.trusted_issuers = configuration["TRUSTED_ISSUERS"]
        self.jwks_timeout = configuration["JWKS_TIMEOUT"]
        self.jwks_debounce = configuration["JWKS_DEBOUNCE"]
        self.jwks_max_age = configuration["JWKS_MAX_AGE"]
        self.token_header_name = configuration["TOKEN_HEADER_NAME"]
        self.algorithms = configuration["ALGORITHMS"]
        self.identifier_claims = configuration["IDENTIFIER_CLAIMS"]
        self.reconciliate_attr = configuration["RECONCILIATE_ATTR"]
        self.allowed_clients = configuration["ALLOWED_CLIENTS"]
        self.required_claims = configuration["REQUIRED_CLAIMS"]
        self.unknown_user_status_code = configuration["UNKNOWN_USER_STATUS_CODE"]

    @staticmethod
    def _import_jwks(jwks_data: dict) -> KeySet:
        """Import the usable keys of a JWKS payload.

        Keys are imported one at a time: ``import_key_set()`` fails the
        whole set on a single unusable key otherwise.

        Parameters
        ----------
        jwks_data : dict
            Raw JWKS payload, as returned by the identity provider.

        Returns
        -------
        KeySet
            The subset of keys that could be imported.

        Raises
        ------
        MissingKeyError
            If none of the payload's keys could be imported.
        """
        keys = []
        for key_data in jwks_data.get("keys", []):
            if not isinstance(key_data, dict):
                log.warning("Skipping unusable JWKS key: not an object (%r)", key_data)
                continue
            try:
                keys.extend(KeySet.import_key_set({"keys": [key_data]}).keys)
            except Exception as e:
                log.warning("Skipping unusable JWKS key %r: %s", key_data.get("kid"), e)
        if not keys:
            raise MissingKeyError("No usable keys in JWKS")
        return KeySet(keys)

    _MAX_JWKS_BYTES = 1024 * 1024

    def _download_jwks(self, deadline: float) -> dict:
        # requests' timeout= only bounds silence between reads, not total
        # size or duration - streamed byte-by-byte with our own checks
        # instead (best-effort: DNS/connect/TLS/headers aren't covered).
        response = requests.get(
            self.jwks_url, timeout=self.jwks_timeout, allow_redirects=False, stream=True
        )
        try:
            if response.is_redirect:
                raise ValueError(
                    f"JWKS_URL must not redirect (got {response.status_code} "
                    f"to {response.headers.get('Location')!r})"
                )
            response.raise_for_status()
            chunks = []
            size = 0
            for chunk in response.iter_content(chunk_size=1):
                if time.monotonic() > deadline:
                    raise TimeoutError(
                        f"JWKS download exceeded its {self.jwks_timeout}s deadline"
                    )
                size += len(chunk)
                if size > self._MAX_JWKS_BYTES:
                    raise ValueError(
                        f"JWKS response exceeds {self._MAX_JWKS_BYTES} bytes"
                    )
                chunks.append(chunk)
            return json.loads(b"".join(chunks))
        finally:
            response.close()

    def _should_attempt_refresh(self, refresh: bool) -> bool:
        now = time.monotonic()  # monotonic: immune to clock adjustments
        cache = self._jwks_cache
        never_attempted = cache["last_attempt"] is None
        debounce_elapsed = not never_attempted and (
            (now - cache["last_attempt"]) >= self.jwks_debounce
        )
        max_age_elapsed = cache["last_success"] is None or (
            (now - cache["last_success"]) >= self.jwks_max_age
        )
        return never_attempted or (
            (refresh or cache["keyset"] is None or max_age_elapsed) and debounce_elapsed
        )

    def _get_jwks(self, refresh=False) -> KeySet:
        cache = self._jwks_cache
        if self._should_attempt_refresh(refresh):
            # Single-flight; blocks (bounded by JWKS_TIMEOUT) only with no
            # cache yet, or on refresh=True since that keyset's known wrong.
            must_wait = refresh or cache["keyset"] is None
            acquired = self._jwks_lock.acquire(
                timeout=self.jwks_timeout if must_wait else 0
            )
            if acquired:
                try:
                    if self._should_attempt_refresh(refresh):
                        self._refresh_jwks()
                finally:
                    self._jwks_lock.release()
            # else another thread is already refreshing; use the cache as-is.
        if cache["keyset"] is None:
            raise KeyError("Failed to load authentication keys from identity provider")
        return cache["keyset"]

    def _refresh_jwks(self) -> None:
        """Fetches a fresh JWKS and updates the cache. Caller must hold
        _jwks_lock."""
        cache = self._jwks_cache
        deadline = time.monotonic() + self.jwks_timeout
        try:
            cache["keyset"] = self._import_jwks(self._download_jwks(deadline))
            cache["last_success"] = time.monotonic()
        except Exception:
            log.exception("Failed to load JWKS from %s", self.jwks_url)
        finally:
            cache["last_attempt"] = time.monotonic()

    # Only these mean the key might be stale (rotation); anything else is
    # just an invalid token.
    _KEY_ROTATION_ERRORS = (InvalidKeyIdError, BadSignatureError, MissingKeyError)

    def _validate_token(self, token: str) -> dict:
        registry = jwt.JWTClaimsRegistry(
            leeway=60,
            iss={"essential": True},
            aud={"essential": True},
            exp={"essential": True},
        )
        try:
            token_obj = jwt.decode(token, self._get_jwks(), algorithms=self.algorithms)
        except KeyError:
            raise  # JWKS unreachable, not an invalid token
        except self._KEY_ROTATION_ERRORS:
            try:
                token_obj = jwt.decode(
                    token, self._get_jwks(refresh=True), algorithms=self.algorithms
                )
            except KeyError:
                raise
            except Exception as e:
                log.info("Token decoding failed: %s", e)
                raise Unauthorized("Invalid identity provider token")
        except Exception as e:
            log.info("Token decoding failed: %s", e)
            raise Unauthorized("Invalid identity provider token")

        try:
            registry.validate(token_obj.claims)
        except ClaimError as e:
            log.info("Token validation failed: %s", e)
            raise Unauthorized("Invalid identity provider token")

        claims = token_obj.claims
        if not self._matches_a_trusted_issuer(claims):
            log.info(
                "Token iss/aud matched no trusted issuer: iss=%r aud=%r",
                claims.get("iss"),
                claims.get("aud"),
            )
            raise Unauthorized("Invalid identity provider token")

        if self.allowed_clients:
            calling_client = claims.get("azp") or claims.get("appid")
            if calling_client not in self.allowed_clients:
                log.info("Rejected token from unauthorized client %r", calling_client)
                raise Unauthorized("Invalid identity provider token")

        if self.required_claims and not any(
            claims.get(name) for name in self.required_claims
        ):
            log.info("Token has none of the required claims %r", self.required_claims)
            raise Unauthorized("Invalid identity provider token")

        return claims

    def _matches_a_trusted_issuer(self, claims: dict) -> bool:
        token_iss = claims.get("iss")
        token_aud = claims.get("aud")
        token_auds = token_aud if isinstance(token_aud, list) else [token_aud]
        return any(
            token_iss == trusted["ISSUER"]
            and not set(token_auds).isdisjoint(trusted["AUDIENCES"])
            for trusted in self.trusted_issuers
        )

    def _resolve_identifier(self, claims: dict) -> str:
        for claim_name in self.identifier_claims:
            value = claims.get(claim_name)
            if isinstance(value, str) and value and "\x00" not in value:
                return value
        raise Unauthorized("Invalid identity provider token")

    def authorize(self) -> Any:
        # No redirect round-trip to finish - /login already does everything.
        raise NotFound(f"{self.id_provider} does not implement the /authorize flow")

    def authenticate(self, *args, **kwargs) -> Union[Response, models.User]:
        bearer = request.headers.get(self.token_header_name, "").strip()
        parts = bearer.split(None, 1)
        if not parts:
            raise Unauthorized("Missing identity provider token")
        token = (
            parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else parts[0]
        )

        claims = self._validate_token(token)
        identifier = self._resolve_identifier(claims)

        user_dict = {self.reconciliate_attr: identifier}
        return self.insert_or_update_role(
            user_dict,
            reconciliate_attr=self.reconciliate_attr,
        )

    def insert_or_update_role(
        self, user_dict, reconciliate_attr="identifiant", **kwargs
    ):
        """Reconciliation only - never provisions a new account."""
        assert reconciliate_attr in user_dict
        try:
            with db.session.begin_nested():  # SAVEPOINT: isolates failures below
                user = db.session.execute(
                    sa.select(models.User)
                    .where(
                        getattr(models.User, reconciliate_attr)
                        == user_dict[reconciliate_attr]
                    )
                    .where(models.User.filter_by_app())
                    # filter_by_app() lets groups through
                    .where(models.User.groupe.is_(False))
                    # not is_(True): active can be NULL
                    .where(models.User.active.isnot(False))
                ).scalar_one_or_none()
        except (MultipleResultsFound, DataError):
            user = None
        if user is None:
            log.info(
                "No existing user with app rights for %s=%r",
                reconciliate_attr,
                user_dict[reconciliate_attr],
            )
            err = Unauthorized("Unknown or unauthorized account")
            err.code = self.unknown_user_status_code
            raise err
        return user
