"""Auth0-compatible login-callback orchestration — SLICE-0053.

Thin orchestration over the accepted boundaries, in accepted call order
(contract §6-§8):

    1. state cookie present and matches the callback's `state` query param
    2. authorization code exchanged for tokens at the provider token endpoint
    3. ID token validated (issuer/audience/signature/expiry/nonce/alg)
    4. JIT `(provider, issuer, subject) -> HullQ Account` mapping, atomic
    5. HullQ session token minted

Any failure short-circuits before the next step; no partial state is
written on failure (the JIT mapping step is the only write, and it only
runs once every earlier step has already succeeded).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.application.broker_login import decode_login_state_cookie
from hullq.domain.broker_access import Provider
from hullq.persistence.broker_identity import get_or_create_account_for_identity
from hullq.security.oidc import (
    AuthProviderConfig,
    InvalidAuthenticationError,
    JwksCache,
    exchange_authorization_code,
    validate_id_token,
)
from hullq.security.session_token import MintedSessionToken, mint_session_token

__all__ = ["CallbackOutcome", "CallbackResult", "complete_login_callback"]


class CallbackOutcome(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    STATE_MISSING_OR_MISMATCH = "STATE_MISSING_OR_MISMATCH"
    INVALID_AUTHENTICATION = "INVALID_AUTHENTICATION"


@dataclass(frozen=True)
class CallbackResult:
    outcome: CallbackOutcome
    session_token: MintedSessionToken | None = None
    next_path: str | None = None

    def __post_init__(self) -> None:
        if self.outcome is CallbackOutcome.SUCCEEDED:
            if self.session_token is None or self.next_path is None:
                raise ValueError(
                    "A SUCCEEDED callback result must carry a session token and next_path"
                )
        elif self.session_token is not None or self.next_path is not None:
            raise ValueError("Only a SUCCEEDED callback result may carry a session token/next_path")


def complete_login_callback(
    conn: Any,
    *,
    config: AuthProviderConfig,
    code: str | None,
    query_state: str | None,
    state_cookie_value: str | None,
    redirect_uri: str,
    session_signing_secret: bytes,
    http_client: Any | None = None,
    jwks_cache: JwksCache | None = None,
) -> CallbackResult:
    login_state = decode_login_state_cookie(state_cookie_value)
    if login_state is None or not query_state or query_state != login_state.state or not code:
        return CallbackResult(outcome=CallbackOutcome.STATE_MISSING_OR_MISMATCH)

    try:
        token_response = exchange_authorization_code(
            config=config, code=code, redirect_uri=redirect_uri, http_client=http_client
        )
        identity = validate_id_token(
            token_response["id_token"],
            config=config,
            expected_nonce=login_state.nonce,
            jwks_cache=jwks_cache,
        )
    except InvalidAuthenticationError:
        return CallbackResult(outcome=CallbackOutcome.INVALID_AUTHENTICATION)

    assert identity.provider is Provider.AUTH0

    with conn.transaction():
        jit_result = get_or_create_account_for_identity(
            conn, provider=identity.provider, issuer=identity.issuer, subject=identity.subject
        )

    minted = mint_session_token(identity, jit_result.account_id, secret=session_signing_secret)
    return CallbackResult(
        outcome=CallbackOutcome.SUCCEEDED, session_token=minted, next_path=login_state.next_path
    )
