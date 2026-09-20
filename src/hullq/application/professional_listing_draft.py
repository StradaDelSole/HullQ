"""Professional listing draft application orchestration — SLICE-0061.

Implements `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md` §3/§7:
thin orchestration over `hullq.domain.professional_listing_draft` (payload/
request validation) and `hullq.persistence.professional_listing_draft`
(durable state), translating a signed `SessionClaims`, an explicit
Organization selection and a raw JSON-decoded request body into one
deterministic outcome FastAPI can render.

Authorization on every request (contract §3.2) reuses the exact accepted
SLICE-0053 Organization workspace boundary
(`hullq.application.broker_workspace_read.get_organization_workspace_result`)
-- never a second reimplementation of membership/MFA/non-enumeration
semantics -- and additionally requires `PUBLISHER` in that exact current
matching ACTIVE membership for every draft-authoring action (list/read/
create/update): contract §1's Objective grants list/create/read/update
uniformly to an Account whose current membership contains `PUBLISHER`, so
this module gates all four uniformly rather than only the two mutating ones.
`OrganizationPublishingEligibility` (`ELIGIBLE`/`UNVERIFIED`/`INELIGIBLE`) is
deliberately never consulted here (contract §3.2 item 5): that gate belongs
only to a later capability that promotes/creates public marketplace truth.

Ownership always derives from the explicit, already-authorized
Organization selection plus `session.account_id` for the audit field
(contract §3.1): none of these functions accept or consult a caller-supplied
owner Organization/Account identity beyond that authorized context. Every
write is wrapped in `with conn.transaction():`, mirroring the accepted
`hullq.application.owner_direct_draft` commit convention.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.domain.listing_draft_payload import InvalidListingDraftPayloadError
from hullq.domain.professional_listing_draft import (
    ProfessionalListingDraftId,
    parse_professional_listing_draft_request,
)
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.persistence.professional_listing_draft import (
    ProfessionalListingDraftRecord,
    ProfessionalListingDraftSortKey,
    ProfessionalListingDraftUpdateOutcome,
    create_professional_listing_draft,
    fetch_professional_listing_draft,
    list_professional_listing_drafts_page,
    update_professional_listing_draft,
)
from hullq.security.session_token import SessionClaims

__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "CreateProfessionalDraftOutcome",
    "CreateProfessionalDraftResult",
    "GetProfessionalDraftOutcome",
    "GetProfessionalDraftResult",
    "InvalidProfessionalDraftCursorError",
    "ListProfessionalDraftsOutcome",
    "ListProfessionalDraftsResult",
    "ProfessionalDraftListPage",
    "UpdateProfessionalDraftOutcome",
    "UpdateProfessionalDraftResult",
    "create_professional_draft_for_organization",
    "get_professional_draft_for_organization",
    "list_professional_drafts_for_organization",
    "professional_draft_record_to_public_dict",
    "update_professional_draft_for_organization",
]

#: Contract §7/§9 v0.1 bounds.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def professional_draft_record_to_public_dict(
    record: ProfessionalListingDraftRecord,
) -> dict[str, Any]:
    """The one wire shape used by list/create/read/update responses alike."""
    body: dict[str, Any] = {
        "draft_id": record.draft_id.value,
        "owner_organization_id": record.owner_organization_id.value,
        "version": record.version,
        "broker_listing_reference": record.broker_listing_reference,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
    body.update(record.payload.to_wire_dict())
    return body


# ---------------------------------------------------------------------------
# Authorization -- reuses the accepted Organization workspace boundary, plus
# the exact-current PUBLISHER draft-authoring role gate (contract §3.2).
# ---------------------------------------------------------------------------


class _DraftActorAuthorizationOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    AUTHORIZED = "AUTHORIZED"


def _authorize_draft_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> _DraftActorAuthorizationOutcome:
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return _DraftActorAuthorizationOutcome.NOT_FOUND_OR_DENIED
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return _DraftActorAuthorizationOutcome.MFA_REQUIRED
    assert workspace_result.context is not None
    if "PUBLISHER" not in workspace_result.context.roles:
        return _DraftActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED
    return _DraftActorAuthorizationOutcome.AUTHORIZED


# ---------------------------------------------------------------------------
# Opaque keyset cursor encode/decode -- mirrors
# hullq.application.broker_inventory_read's identical strict-canonical-
# base64url discipline, over (updated_at, draft_id) instead of
# (created_at, native_listing_id).
# ---------------------------------------------------------------------------


class InvalidProfessionalDraftCursorError(ValueError):
    """*cursor* is not a validly encoded draft-list continuation cursor.

    Raised only for a malformed/tampered cursor -- never for a merely stale
    one. A stale-but-well-formed cursor simply yields zero further rows.
    """


_CURSOR_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _cursor_b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _cursor_b64url_decode(text: str) -> bytes:
    if not text or not _CURSOR_SEGMENT_RE.fullmatch(text):
        raise InvalidProfessionalDraftCursorError(
            "cursor is not strict, canonical, unpadded base64url"
        )
    padded = text + ("=" * ((-len(text)) % 4))
    try:
        decoded = base64.b64decode(padded.encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidProfessionalDraftCursorError("malformed cursor encoding") from exc
    if _cursor_b64url_encode(decoded) != text:
        raise InvalidProfessionalDraftCursorError(
            "cursor is not the canonical base64url encoding of its bytes"
        )
    return decoded


def _encode_cursor(key: ProfessionalListingDraftSortKey) -> str:
    payload = {
        "updated_at": key.updated_at.isoformat(),
        "draft_id": key.draft_id.value,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _cursor_b64url_encode(raw)


def _decode_cursor(cursor: str) -> ProfessionalListingDraftSortKey:
    if not isinstance(cursor, str) or not cursor:
        raise InvalidProfessionalDraftCursorError("cursor must be a non-empty string")

    raw = _cursor_b64url_decode(cursor)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidProfessionalDraftCursorError("malformed cursor payload") from exc
    if not isinstance(payload, dict):
        raise InvalidProfessionalDraftCursorError("malformed cursor payload")

    updated_at_raw = payload.get("updated_at")
    draft_id_raw = payload.get("draft_id")
    if not isinstance(updated_at_raw, str) or not updated_at_raw:
        raise InvalidProfessionalDraftCursorError("malformed cursor: updated_at")
    if not isinstance(draft_id_raw, str) or not draft_id_raw:
        raise InvalidProfessionalDraftCursorError("malformed cursor: draft_id")

    try:
        updated_at = datetime.fromisoformat(updated_at_raw)
    except ValueError as exc:
        raise InvalidProfessionalDraftCursorError("malformed cursor: updated_at") from exc
    if updated_at.tzinfo is None or updated_at.utcoffset() is None:
        raise InvalidProfessionalDraftCursorError(
            "malformed cursor: updated_at must be timezone-aware"
        )

    return ProfessionalListingDraftSortKey(
        updated_at=updated_at, draft_id=ProfessionalListingDraftId(draft_id_raw)
    )


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


class ListProfessionalDraftsOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    INVALID_PAGE_SIZE = "INVALID_PAGE_SIZE"
    INVALID_CURSOR = "INVALID_CURSOR"
    OK = "OK"


@dataclass(frozen=True)
class ProfessionalDraftListPage:
    items: tuple[ProfessionalListingDraftRecord, ...]
    next_cursor: str | None

    def to_public_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "drafts": [professional_draft_record_to_public_dict(r) for r in self.items]
        }
        if self.next_cursor is not None:
            result["next_cursor"] = self.next_cursor
        return result


@dataclass(frozen=True)
class ListProfessionalDraftsResult:
    outcome: ListProfessionalDraftsOutcome
    page: ProfessionalDraftListPage | None = None

    def __post_init__(self) -> None:
        if self.outcome is ListProfessionalDraftsOutcome.OK:
            if self.page is None:
                raise ValueError("An OK list result must carry a page")
        elif self.page is not None:
            raise ValueError("Only an OK list result may carry a page")


def list_professional_drafts_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    *,
    page_size: int | None,
    cursor: str | None,
) -> ListProfessionalDraftsResult:
    """List only the selected, authorized Organization's own drafts
    (contract §3/§7/§9)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_draft_actor(conn, session, organization_id)
    if auth is _DraftActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return ListProfessionalDraftsResult(
            outcome=ListProfessionalDraftsOutcome.NOT_FOUND_OR_DENIED
        )
    if auth is _DraftActorAuthorizationOutcome.MFA_REQUIRED:
        return ListProfessionalDraftsResult(outcome=ListProfessionalDraftsOutcome.MFA_REQUIRED)
    if auth is _DraftActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return ListProfessionalDraftsResult(
            outcome=ListProfessionalDraftsOutcome.PUBLISHER_ROLE_REQUIRED
        )

    if page_size is not None and not (1 <= page_size <= MAX_PAGE_SIZE):
        return ListProfessionalDraftsResult(outcome=ListProfessionalDraftsOutcome.INVALID_PAGE_SIZE)
    resolved_page_size = page_size if page_size is not None else DEFAULT_PAGE_SIZE

    after: ProfessionalListingDraftSortKey | None = None
    if cursor is not None:
        try:
            after = _decode_cursor(cursor)
        except InvalidProfessionalDraftCursorError:
            return ListProfessionalDraftsResult(
                outcome=ListProfessionalDraftsOutcome.INVALID_CURSOR
            )

    # Fetch one extra row to determine whether another page exists without a
    # separate total-count query.
    records = list_professional_listing_drafts_page(
        conn,
        owner_organization_id=organization_id,
        limit=resolved_page_size + 1,
        after=after,
    )
    has_more = len(records) > resolved_page_size
    page_records = records[:resolved_page_size]

    next_cursor = (
        _encode_cursor(
            ProfessionalListingDraftSortKey(
                updated_at=page_records[-1].updated_at, draft_id=page_records[-1].draft_id
            )
        )
        if has_more and page_records
        else None
    )
    return ListProfessionalDraftsResult(
        outcome=ListProfessionalDraftsOutcome.OK,
        page=ProfessionalDraftListPage(items=tuple(page_records), next_cursor=next_cursor),
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


class CreateProfessionalDraftOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    CREATED = "CREATED"


@dataclass(frozen=True)
class CreateProfessionalDraftResult:
    outcome: CreateProfessionalDraftOutcome
    record: ProfessionalListingDraftRecord | None = None

    def __post_init__(self) -> None:
        if self.outcome is CreateProfessionalDraftOutcome.CREATED and self.record is None:
            raise ValueError("A CREATED result must carry the new record")
        if self.outcome is not CreateProfessionalDraftOutcome.CREATED and self.record is not None:
            raise ValueError("Only a CREATED result may carry a record")


def create_professional_draft_for_organization(
    conn: Any, session: SessionClaims, organization_id_value: str, raw_initial_request: Any
) -> CreateProfessionalDraftResult:
    """Create one draft owned by the selected, authorized Organization.

    *raw_initial_request* is optional: `None` (no request body) is treated
    identically to an explicit empty object. An invalid request writes zero
    rows.
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_draft_actor(conn, session, organization_id)
    if auth is _DraftActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return CreateProfessionalDraftResult(
            outcome=CreateProfessionalDraftOutcome.NOT_FOUND_OR_DENIED
        )
    if auth is _DraftActorAuthorizationOutcome.MFA_REQUIRED:
        return CreateProfessionalDraftResult(outcome=CreateProfessionalDraftOutcome.MFA_REQUIRED)
    if auth is _DraftActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return CreateProfessionalDraftResult(
            outcome=CreateProfessionalDraftOutcome.PUBLISHER_ROLE_REQUIRED
        )

    try:
        request = parse_professional_listing_draft_request(
            {} if raw_initial_request is None else raw_initial_request
        )
    except InvalidListingDraftPayloadError:
        return CreateProfessionalDraftResult(outcome=CreateProfessionalDraftOutcome.INVALID_PAYLOAD)

    # The authorization check above already issued read-only queries on
    # *conn*, which (psycopg default autocommit=False) leaves an implicit
    # transaction open. Ending it here first means the `with
    # conn.transaction():` below is a real, independently committing
    # transaction rather than a nested SAVEPOINT whose commit would leave
    # the still-open outer (authorization) transaction -- and therefore
    # this very INSERT -- uncommitted when the caller later closes *conn*.
    conn.commit()
    with conn.transaction():
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=organization_id,
            created_by_account_id=session.account_id,
            broker_listing_reference=request.broker_listing_reference,
            payload=request.common,
        )
    return CreateProfessionalDraftResult(
        outcome=CreateProfessionalDraftOutcome.CREATED, record=record
    )


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


class GetProfessionalDraftOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    DRAFT_NOT_FOUND = "DRAFT_NOT_FOUND"
    FOUND = "FOUND"


@dataclass(frozen=True)
class GetProfessionalDraftResult:
    outcome: GetProfessionalDraftOutcome
    record: ProfessionalListingDraftRecord | None = None

    def __post_init__(self) -> None:
        if self.outcome is GetProfessionalDraftOutcome.FOUND and self.record is None:
            raise ValueError("A FOUND result must carry a record")
        if self.outcome is not GetProfessionalDraftOutcome.FOUND and self.record is not None:
            raise ValueError("Only a FOUND result may carry a record")


def get_professional_draft_for_organization(
    conn: Any, session: SessionClaims, organization_id_value: str, draft_id_value: str
) -> GetProfessionalDraftResult:
    """Read one draft, scoped to the selected, authorized Organization
    (contract §3/§7)."""
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_draft_actor(conn, session, organization_id)
    if auth is _DraftActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return GetProfessionalDraftResult(outcome=GetProfessionalDraftOutcome.NOT_FOUND_OR_DENIED)
    if auth is _DraftActorAuthorizationOutcome.MFA_REQUIRED:
        return GetProfessionalDraftResult(outcome=GetProfessionalDraftOutcome.MFA_REQUIRED)
    if auth is _DraftActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return GetProfessionalDraftResult(
            outcome=GetProfessionalDraftOutcome.PUBLISHER_ROLE_REQUIRED
        )

    record = fetch_professional_listing_draft(
        conn,
        draft_id=ProfessionalListingDraftId(draft_id_value),
        owner_organization_id=organization_id,
    )
    if record is None:
        return GetProfessionalDraftResult(outcome=GetProfessionalDraftOutcome.DRAFT_NOT_FOUND)
    return GetProfessionalDraftResult(outcome=GetProfessionalDraftOutcome.FOUND, record=record)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class UpdateProfessionalDraftOutcome(StrEnum):
    NOT_FOUND_OR_DENIED = "NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    DRAFT_NOT_FOUND = "DRAFT_NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    UPDATED = "UPDATED"


@dataclass(frozen=True)
class UpdateProfessionalDraftResult:
    outcome: UpdateProfessionalDraftOutcome
    record: ProfessionalListingDraftRecord | None = None

    def __post_init__(self) -> None:
        if self.outcome is UpdateProfessionalDraftOutcome.UPDATED and self.record is None:
            raise ValueError("An UPDATED result must carry the new record")
        if self.outcome is not UpdateProfessionalDraftOutcome.UPDATED and self.record is not None:
            raise ValueError("Only an UPDATED result may carry a record")


def update_professional_draft_for_organization(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    draft_id_value: str,
    raw_body: Any,
) -> UpdateProfessionalDraftResult:
    """Update one draft's full bounded payload iff `expected_version` matches.

    *raw_body* must be a JSON object carrying `expected_version` (a positive
    int) plus the bounded professional draft request shape (contract §4/§5);
    any other shape is `INVALID_PAYLOAD` (400), writing zero rows.
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    auth = _authorize_draft_actor(conn, session, organization_id)
    if auth is _DraftActorAuthorizationOutcome.NOT_FOUND_OR_DENIED:
        return UpdateProfessionalDraftResult(
            outcome=UpdateProfessionalDraftOutcome.NOT_FOUND_OR_DENIED
        )
    if auth is _DraftActorAuthorizationOutcome.MFA_REQUIRED:
        return UpdateProfessionalDraftResult(outcome=UpdateProfessionalDraftOutcome.MFA_REQUIRED)
    if auth is _DraftActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return UpdateProfessionalDraftResult(
            outcome=UpdateProfessionalDraftOutcome.PUBLISHER_ROLE_REQUIRED
        )

    if not isinstance(raw_body, dict):
        return UpdateProfessionalDraftResult(outcome=UpdateProfessionalDraftOutcome.INVALID_PAYLOAD)

    body = dict(raw_body)
    expected_version = body.pop("expected_version", None)
    if (
        not isinstance(expected_version, int)
        or isinstance(expected_version, bool)
        or expected_version <= 0
    ):
        return UpdateProfessionalDraftResult(outcome=UpdateProfessionalDraftOutcome.INVALID_PAYLOAD)

    try:
        request = parse_professional_listing_draft_request(body)
    except InvalidListingDraftPayloadError:
        return UpdateProfessionalDraftResult(outcome=UpdateProfessionalDraftOutcome.INVALID_PAYLOAD)

    # See the identical comment in create_professional_draft_for_organization:
    # ends the authorization check's implicit read transaction first, so the
    # write below commits independently rather than as an uncommitted
    # nested SAVEPOINT.
    conn.commit()
    with conn.transaction():
        result = update_professional_listing_draft(
            conn,
            draft_id=ProfessionalListingDraftId(draft_id_value),
            owner_organization_id=organization_id,
            broker_listing_reference=request.broker_listing_reference,
            payload=request.common,
            expected_version=expected_version,
        )

    if result.outcome is ProfessionalListingDraftUpdateOutcome.UPDATED:
        assert result.record is not None
        return UpdateProfessionalDraftResult(
            outcome=UpdateProfessionalDraftOutcome.UPDATED, record=result.record
        )
    if result.outcome is ProfessionalListingDraftUpdateOutcome.VERSION_CONFLICT:
        return UpdateProfessionalDraftResult(
            outcome=UpdateProfessionalDraftOutcome.VERSION_CONFLICT
        )
    return UpdateProfessionalDraftResult(outcome=UpdateProfessionalDraftOutcome.DRAFT_NOT_FOUND)
