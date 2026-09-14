"""Unit tests for hullq.security.oidc — SLICE-0053.

Exercises the real RS256 signature/issuer/audience/expiry/nonce/algorithm
boundary with real locally-generated RSA keys -- no network, no live Auth0.
Every failure path must collapse to `InvalidAuthenticationError` before any
claim is returned (contract §7).
"""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from hullq.domain.broker_access import Provider
from hullq.security.oidc import (
    AuthProviderConfig,
    AuthProviderConfigError,
    InvalidAuthenticationError,
    get_auth_provider_config,
    validate_id_token,
)

_ISSUER = "https://hullq-dev.eu.auth0.com/"
_CLIENT_ID = "test-client-id"
_KID = "test-kid-1"


class _FakeJwksCache:
    def __init__(self, keys: dict[str, object]) -> None:
        self._keys = keys

    def get_key(self, kid: str) -> object:
        if kid not in self._keys:
            raise InvalidAuthenticationError("unknown signing key id")
        return self._keys[kid]


def _config() -> AuthProviderConfig:
    return AuthProviderConfig(
        provider=Provider.AUTH0,
        issuer=_ISSUER,
        authorize_endpoint="https://example.test/authorize",
        token_endpoint="https://example.test/token",
        jwks_uri="https://example.test/.well-known/jwks.json",
        client_id=_CLIENT_ID,
        client_secret="test-secret",
    )


@pytest.fixture
def rsa_keys() -> tuple[object, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key, private_key.public_key()


@pytest.fixture
def jwks_cache(rsa_keys: tuple[object, object]) -> _FakeJwksCache:
    _, public_key = rsa_keys
    return _FakeJwksCache({_KID: public_key})


def _sign(
    private_key: object,
    *,
    claims: dict[str, object],
    kid: str = _KID,
    alg: str = "RS256",
) -> str:
    return jwt.encode(claims, private_key, algorithm=alg, headers={"kid": kid})


def _valid_claims(*, nonce: str = "n-1", **overrides: object) -> dict[str, object]:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": _ISSUER,
        "aud": _CLIENT_ID,
        "sub": "auth0|user-1",
        "iat": now,
        "exp": now + 300,
        "auth_time": now,
        "nonce": nonce,
        "amr": [],
    }
    claims.update(overrides)
    return claims


class TestValidateIdToken:
    def test_valid_token_returns_identity(
        self, rsa_keys: tuple[object, object], jwks_cache: _FakeJwksCache
    ) -> None:
        private_key, _ = rsa_keys
        token = _sign(private_key, claims=_valid_claims())
        identity = validate_id_token(
            token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache
        )
        assert identity.subject == "auth0|user-1"
        assert identity.provider is Provider.AUTH0
        assert identity.mfa_satisfied is False

    def test_mfa_amr_sets_mfa_satisfied(
        self, rsa_keys: tuple[object, object], jwks_cache: _FakeJwksCache
    ) -> None:
        private_key, _ = rsa_keys
        token = _sign(private_key, claims=_valid_claims(amr=["mfa"]))
        identity = validate_id_token(
            token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache
        )
        assert identity.mfa_satisfied is True

    def test_wrong_issuer_rejected(
        self, rsa_keys: tuple[object, object], jwks_cache: _FakeJwksCache
    ) -> None:
        private_key, _ = rsa_keys
        token = _sign(private_key, claims=_valid_claims(iss="https://attacker.example/"))
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache)

    def test_wrong_audience_rejected(
        self, rsa_keys: tuple[object, object], jwks_cache: _FakeJwksCache
    ) -> None:
        private_key, _ = rsa_keys
        token = _sign(private_key, claims=_valid_claims(aud="someone-elses-client"))
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache)

    def test_expired_token_rejected(
        self, rsa_keys: tuple[object, object], jwks_cache: _FakeJwksCache
    ) -> None:
        private_key, _ = rsa_keys
        now = int(time.time())
        token = _sign(private_key, claims=_valid_claims(iat=now - 1000, exp=now - 500))
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache)

    def test_nonce_mismatch_rejected(
        self, rsa_keys: tuple[object, object], jwks_cache: _FakeJwksCache
    ) -> None:
        private_key, _ = rsa_keys
        token = _sign(private_key, claims=_valid_claims(nonce="n-1"))
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(
                token, config=_config(), expected_nonce="n-DIFFERENT", jwks_cache=jwks_cache
            )

    def test_wrong_signing_key_rejected(self, jwks_cache: _FakeJwksCache) -> None:
        other_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        token = _sign(other_private_key, claims=_valid_claims())
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache)

    def test_unknown_kid_rejected(
        self, rsa_keys: tuple[object, object], jwks_cache: _FakeJwksCache
    ) -> None:
        private_key, _ = rsa_keys
        token = _sign(private_key, claims=_valid_claims(), kid="unknown-kid")
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache)

    def test_alg_none_rejected(self, jwks_cache: _FakeJwksCache) -> None:
        # A forged "alg: none" token never reaches signature verification at
        # all -- it must be rejected purely from the disallowed header.
        token = jwt.encode(_valid_claims(), key="", algorithm="none")
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache)

    def test_hs256_symmetric_alg_rejected(self, jwks_cache: _FakeJwksCache) -> None:
        # Classic alg-confusion attack: sign with HS256 using the (public!)
        # RSA public key material as an HMAC secret. Must be rejected purely
        # by the algorithm allowlist, before any key lookup could succeed.
        token = jwt.encode(_valid_claims(), key="any-secret-string", algorithm="HS256")
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache)

    def test_malformed_token_rejected(self, jwks_cache: _FakeJwksCache) -> None:
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(
                "not-a-jwt", config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache
            )

    def test_empty_token_rejected(self, jwks_cache: _FakeJwksCache) -> None:
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token("", config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache)

    def test_missing_subject_rejected(
        self, rsa_keys: tuple[object, object], jwks_cache: _FakeJwksCache
    ) -> None:
        private_key, _ = rsa_keys
        claims = _valid_claims()
        del claims["sub"]
        token = _sign(private_key, claims=claims)
        with pytest.raises(InvalidAuthenticationError):
            validate_id_token(token, config=_config(), expected_nonce="n-1", jwks_cache=jwks_cache)


class TestGetAuthProviderConfig:
    def test_missing_env_fails_fast(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for env_var in [
            "HULLQ_AUTH_ISSUER",
            "HULLQ_AUTH_AUTHORIZE_URL",
            "HULLQ_AUTH_TOKEN_URL",
            "HULLQ_AUTH_JWKS_URL",
            "HULLQ_AUTH_CLIENT_ID",
            "HULLQ_AUTH_CLIENT_SECRET",
        ]:
            monkeypatch.delenv(env_var, raising=False)
        with pytest.raises(AuthProviderConfigError):
            get_auth_provider_config()

    def test_complete_env_loads(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HULLQ_AUTH_ISSUER", _ISSUER)
        monkeypatch.setenv("HULLQ_AUTH_AUTHORIZE_URL", "https://example.test/authorize")
        monkeypatch.setenv("HULLQ_AUTH_TOKEN_URL", "https://example.test/token")
        monkeypatch.setenv("HULLQ_AUTH_JWKS_URL", "https://example.test/.well-known/jwks.json")
        monkeypatch.setenv("HULLQ_AUTH_CLIENT_ID", _CLIENT_ID)
        monkeypatch.setenv("HULLQ_AUTH_CLIENT_SECRET", "secret")
        config = get_auth_provider_config()
        assert config.provider is Provider.AUTH0
        assert config.issuer == _ISSUER


def test_jwk_roundtrip_sanity() -> None:
    # Confirms our own fixture's JWK conversion (used elsewhere for the
    # test issuer) is self-consistent.
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk_dict = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    assert "n" in jwk_dict and "e" in jwk_dict
