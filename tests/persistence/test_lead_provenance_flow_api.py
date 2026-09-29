"""FastAPI integration tests for SLICE-0071 Finding A amendment — real
acquisition (UTM) and discovery-surface provenance wired through the actual
buyer-facing contact flow.

Covers `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md` §8B as
amended: bounded UTM evidence carried through the real `/contact` route;
signed, server-verified discovery-surface tokens minted by the real
`/api/search/{locale}` and `/api/listings/{id}` routes (the exact endpoints
`web/src/lib/searchApi.ts`, `web/src/lib/publicListingApi.ts` and
`web/src/pages/api/shortlist/resolve.ts` call); and the independent-review
invariant that no arbitrary client-supplied discovery value can ever become
authoritative.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

from hullq.domain.buyer_lead import LeadId
from hullq.domain.lead_provenance import DiscoverySurface
from hullq.domain.market_identity import (
    BoatDesignRef,
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.media_gallery import MediaSourceKind
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    DraftClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
)
from hullq.domain.provenance import SubjectKind
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    MembershipRole,
    MembershipState,
    OrganizationMembership,
    OrganizationMembershipId,
    OrganizationPublishingEligibility,
    ProfessionalCategory,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.broker_identity import seed_marketplace_organization
from hullq.persistence.lead_provenance import fetch_lead_acquisition_provenance
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.search.draft_max_design_bridge import DRAFT_MAX_FIELD_POINTER

from ._field_resolution_support import admit_resolved_draft_max

_PREVIEW_SECRET = b"0" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_NAME = "x-hullq-requested-with"
_CSRF_HEADER_VALUE = "marketplace-buyer-lead-v1"

#: Mirrors `test_inventory_search_classification.py`'s identical fixture:
#: a real durable `canonical_boat_designs` row + a real `resolved`
#: FieldResolution admitting it, so `draft_max` search classifies a
#: genuinely CONFIRMED match through the real, unmodified production path
#: (post-FieldResolution-blocker amendment) -- never a monkeypatched
#: design-qualification shortcut.
_DESIGN_ID = "BD-0071-PROV"
_DESIGN_BASELINE_DRAFT_MAX_M = Decimal("1.30")


def _admit_search_design(api_url: str) -> None:
    conn = psycopg.connect(api_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
                "VALUES (%s, %s, %s)",
                ["BM-0071-PROV", "Model BM-0071-PROV", "0" * 64],
            )
            cur.execute(
                "INSERT INTO canonical_boat_designs "
                "(id, boat_model_id, generation, designers, baseline, named_variants, "
                " design_options, quality, content_hash) "
                "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
                [
                    _DESIGN_ID,
                    "BM-0071-PROV",
                    "{}",
                    "[]",
                    json.dumps(
                        {"dimensions": {"draft_max_m": float(_DESIGN_BASELINE_DRAFT_MAX_M)}}
                    ),
                    "[]",
                    "[]",
                    "{}",
                    "1" * 64,
                ],
            )
        conn.commit()
        admit_resolved_draft_max(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=_DESIGN_ID,
            field_pointer=DRAFT_MAX_FIELD_POINTER,
            value=_DESIGN_BASELINE_DRAFT_MAX_M,
            resolution_id="FR-0071-PROV-BASELINE",
        )
    finally:
        conn.close()


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def _create_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()


def _drop_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    finally:
        conn.close()


@pytest.fixture()
def api_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0071prov_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


@pytest.fixture()
def client(api_url: str, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    from hullq.api.app import create_app

    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    app = create_app(
        database_url=api_url,
        preview_signing_secret=_PREVIEW_SECRET,
        session_signing_secret=b"7" * 32,
        web_origin=_WEB_ORIGIN,
    )
    test_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
    try:
        yield test_client
    finally:
        test_client.close()


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(
    org: MarketplaceOrganization, account: AccountId, membership_id: str
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _attach_ready_cover_image(
    conn: Any, *, listing_id: str, org: MarketplaceOrganization, account: AccountId
) -> None:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [account.value],
            )
        seed_marketplace_organization(conn, org)
        asset = insert_approved_media_asset(
            conn,
            owner_organization_id=org.id,
            uploaded_by_account_id=account,
            rights_declared=True,
            source_kind=MediaSourceKind.BROKER_UPLOAD,
            source_reference=None,
            original_object_key=f"original/{listing_id}",
            derivative_object_key=f"derivative/{listing_id}",
            content_hash=f"hash-{listing_id}",
            mime_type="image/jpeg",
            width=800,
            height=600,
            byte_size=12345,
        )
        placement_result = create_uploaded_image_placement(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_asset=asset,
        )
        assert placement_result.media_placement_id is not None
        assert placement_result.gallery_version is not None
        cover_result = set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement_result.media_placement_id,
            expected_version=placement_result.gallery_version,
        )
        assert cover_result.outcome.value == "SET", cover_result


def _publish_listing(
    api_url: str, *, listing_id: str, draft: Decimal | None = None
) -> tuple[AccountId, MarketplaceOrganization]:
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(f"ACC-{listing_id}")
        org = _org(f"ORG-{listing_id}")
        membership = _membership(org, account, f"OM-{listing_id}")

        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(f"PB-{listing_id}"),
                boat_design_ref=BoatDesignRef(_DESIGN_ID) if draft is not None else None,
            ),
        )
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(f"ME-{listing_id}"),
                physical_boat_id=PhysicalBoatId(f"PB-{listing_id}"),
            ),
        )
        create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(listing_id),
                market_episode_id=MarketEpisodeId(f"ME-{listing_id}"),
            ),
        )
        write_native_listing_offer_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
            expected_current_revision_id=None,
            offer=NativeListingOfferSnapshot(
                asking_price_mode=AskingPriceMode.AMOUNT,
                location_country="FR",
                broker_description="A well-maintained cruising sloop.",
                asking_price_amount=Decimal("125000.00"),
                currency="EUR",
            ),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Oceanis 30.1",
                build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
                draft=(
                    DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=draft)
                    if draft is not None
                    else None
                ),
            ),
        )
        _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
        publish_result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert publish_result.status.value == "transitioned", publish_result
        conn.commit()
        return account, org
    finally:
        conn.close()


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, _CSRF_HEADER_NAME: _CSRF_HEADER_VALUE}


def _contact_url(listing_id: str) -> str:
    return f"/api/listings/{listing_id}/contact"


def _submit_contact(
    client: TestClient, listing_id: str, *, op_suffix: str, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    body = {
        "submission_operation_id": f"OP-{listing_id}-{op_suffix}",
        "name": "Jane Buyer",
        "email": "jane@example.com",
        "message": "Interested in this boat.",
        **(extra or {}),
    }
    response = client.post(_contact_url(listing_id), headers=_csrf_headers(), json=body)
    assert response.status_code in (200, 201), response.text
    return response.json()


def _fetch_provenance(api_url: str, lead_id_value: str) -> Any:
    conn = psycopg.connect(api_url)
    try:
        return fetch_lead_acquisition_provenance(conn, LeadId(lead_id_value))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Acquisition (UTM) evidence through the real contact route
# ---------------------------------------------------------------------------


def test_all_five_utm_fields_persist_when_present(client: TestClient, api_url: str) -> None:
    _publish_listing(api_url, listing_id="NLP1")
    body = _submit_contact(
        client,
        "NLP1",
        op_suffix="A",
        extra={
            "utm_source": "google",
            "utm_medium": "cpc",
            "utm_campaign": "summer-sale",
            "utm_term": "sailboat for sale",
            "utm_content": "ad-variant-1",
        },
    )
    provenance = _fetch_provenance(api_url, body["lead_id"])
    assert provenance is not None
    assert provenance.utm_source == "google"
    assert provenance.utm_medium == "cpc"
    assert provenance.utm_campaign == "summer-sale"
    assert provenance.utm_term == "sailboat for sale"
    assert provenance.utm_content == "ad-variant-1"
    from hullq.domain.lead_provenance import AcquisitionChannel

    assert provenance.acquisition_channel is AcquisitionChannel.PAID_SEARCH


def test_missing_utm_remains_unknown_never_guessed(client: TestClient, api_url: str) -> None:
    _publish_listing(api_url, listing_id="NLP2")
    body = _submit_contact(client, "NLP2", op_suffix="A")
    provenance = _fetch_provenance(api_url, body["lead_id"])
    assert provenance is not None
    assert provenance.utm_source is None
    assert provenance.utm_medium is None
    assert provenance.utm_campaign is None
    from hullq.domain.lead_provenance import AcquisitionChannel

    assert provenance.acquisition_channel is AcquisitionChannel.UNKNOWN


def test_malformed_utm_cannot_corrupt_or_fail_lead_creation(
    client: TestClient, api_url: str
) -> None:
    _publish_listing(api_url, listing_id="NLP3")
    oversized = "x" * 5000
    body = _submit_contact(
        client,
        "NLP3",
        op_suffix="A",
        extra={"utm_source": oversized, "utm_medium": "\x00bad\x01"},
    )
    assert body["status"] == "CREATED"
    provenance = _fetch_provenance(api_url, body["lead_id"])
    assert provenance is not None
    # Malformed values degrade to absent evidence -- never persisted verbatim,
    # never a distinguishable error, and never a failed Lead creation.
    assert provenance.utm_source is None
    assert provenance.utm_medium is None


# ---------------------------------------------------------------------------
# Discovery surface: TECHNICAL_SEARCH via the real search endpoint
# ---------------------------------------------------------------------------


def test_technical_search_discovery_path_persists_technical_search(
    client: TestClient, api_url: str
) -> None:
    _admit_search_design(api_url)
    _publish_listing(api_url, listing_id="NLP4", draft=Decimal("1.40"))
    search_response = client.get("/api/search/en?draft_max=1.6")
    assert search_response.status_code == 200
    matches = search_response.json()["confirmed_matches"]
    assert any(m["native_listing_id"] == "NLP4" for m in matches), matches
    match = next(m for m in matches if m["native_listing_id"] == "NLP4")
    assert isinstance(match["discovery_token"], str) and match["discovery_token"]

    body = _submit_contact(
        client, "NLP4", op_suffix="A", extra={"discovery_token": match["discovery_token"]}
    )
    provenance = _fetch_provenance(api_url, body["lead_id"])
    assert provenance is not None
    assert provenance.discovery_surface is DiscoverySurface.TECHNICAL_SEARCH


def test_technical_search_token_is_bound_to_its_own_listing_only(
    client: TestClient, api_url: str
) -> None:
    _admit_search_design(api_url)
    _publish_listing(api_url, listing_id="NLP4B", draft=Decimal("1.40"))
    _publish_listing(api_url, listing_id="NLP4C")
    search_response = client.get("/api/search/en?draft_max=1.6")
    match = next(
        m for m in search_response.json()["confirmed_matches"] if m["native_listing_id"] == "NLP4B"
    )
    # Replaying NLP4B's token against a *different* listing's contact route
    # must never be accepted -- the listing binding is checked, not merely
    # the signature.
    body = _submit_contact(
        client, "NLP4C", op_suffix="A", extra={"discovery_token": match["discovery_token"]}
    )
    provenance = _fetch_provenance(api_url, body["lead_id"])
    assert provenance is not None
    assert provenance.discovery_surface is DiscoverySurface.UNKNOWN


# ---------------------------------------------------------------------------
# Discovery surface: SHORTLIST / COMPARE via the public listing endpoint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("context", "expected"),
    [("SHORTLIST", DiscoverySurface.SHORTLIST), ("COMPARE", DiscoverySurface.COMPARE)],
)
def test_shortlist_and_compare_discovery_paths_persist_correctly(
    client: TestClient, api_url: str, context: str, expected: DiscoverySurface
) -> None:
    listing_id = f"NLP5{context[0]}"
    _publish_listing(api_url, listing_id=listing_id)
    listing_response = client.get(f"/api/listings/{listing_id}?discovery_surface_context={context}")
    assert listing_response.status_code == 200
    discovery_token = listing_response.json()["discovery_token"]

    body = _submit_contact(
        client, listing_id, op_suffix="A", extra={"discovery_token": discovery_token}
    )
    provenance = _fetch_provenance(api_url, body["lead_id"])
    assert provenance is not None
    assert provenance.discovery_surface is expected


# ---------------------------------------------------------------------------
# Discovery surface: DIRECT_LISTING / INTERNAL_BROWSE via referrer_hint
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("hint", "expected"),
    [
        ("NONE", DiscoverySurface.DIRECT_LISTING),
        ("EXTERNAL", DiscoverySurface.DIRECT_LISTING),
        ("INTERNAL", DiscoverySurface.INTERNAL_BROWSE),
    ],
)
def test_referrer_hint_resolves_direct_and_internal_browse(
    client: TestClient, api_url: str, hint: str, expected: DiscoverySurface
) -> None:
    listing_id = f"NLP6{hint[0]}"
    _publish_listing(api_url, listing_id=listing_id)
    listing_response = client.get(f"/api/listings/{listing_id}?referrer_hint={hint}")
    assert listing_response.status_code == 200
    discovery_token = listing_response.json()["discovery_token"]

    body = _submit_contact(
        client, listing_id, op_suffix="A", extra={"discovery_token": discovery_token}
    )
    provenance = _fetch_provenance(api_url, body["lead_id"])
    assert provenance is not None
    assert provenance.discovery_surface is expected


def test_no_evidence_at_all_yields_no_token_and_stays_unknown(
    client: TestClient, api_url: str
) -> None:
    listing_id = "NLP6X"
    _publish_listing(api_url, listing_id=listing_id)
    listing_response = client.get(f"/api/listings/{listing_id}")
    assert listing_response.status_code == 200
    assert "discovery_token" not in listing_response.json()

    body = _submit_contact(client, listing_id, op_suffix="A")
    provenance = _fetch_provenance(api_url, body["lead_id"])
    assert provenance is not None
    assert provenance.discovery_surface is DiscoverySurface.UNKNOWN


# ---------------------------------------------------------------------------
# No arbitrary client-supplied string can become authoritative provenance
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forged_token",
    [
        "SHORTLIST",
        "TECHNICAL_SEARCH",
        '{"surface":"SHORTLIST","nlid":"NLP7"}',
        "not-even-token-shaped",
    ],
)
def test_arbitrary_client_supplied_discovery_value_is_never_authoritative(
    client: TestClient, api_url: str, forged_token: str
) -> None:
    _publish_listing(api_url, listing_id="NLP7")
    body = _submit_contact(
        client, "NLP7", op_suffix=forged_token[:8], extra={"discovery_token": forged_token}
    )
    provenance = _fetch_provenance(api_url, body["lead_id"])
    assert provenance is not None
    assert provenance.discovery_surface is DiscoverySurface.UNKNOWN


# ---------------------------------------------------------------------------
# Exact retry creates no second/conflicting provenance row
# ---------------------------------------------------------------------------


def test_exact_retry_creates_no_second_provenance_row(client: TestClient, api_url: str) -> None:
    _publish_listing(api_url, listing_id="NLP8")
    first = _submit_contact(
        client, "NLP8", op_suffix="SAME", extra={"utm_source": "google", "utm_medium": "cpc"}
    )
    assert first["status"] == "CREATED"

    shortlist_response = client.get("/api/listings/NLP8?discovery_surface_context=SHORTLIST")
    different_token = shortlist_response.json()["discovery_token"]
    second = client.post(
        _contact_url("NLP8"),
        headers=_csrf_headers(),
        json={
            "submission_operation_id": "OP-NLP8-SAME",
            "name": "Jane Buyer",
            "email": "jane@example.com",
            "message": "Interested in this boat.",
            "utm_source": "google",
            "utm_medium": "cpc",
            "discovery_token": different_token,
        },
    ).json()
    assert second["status"] == "ALREADY_EXISTS"
    assert second["lead_id"] == first["lead_id"]

    conn = psycopg.connect(api_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM lead_acquisition_provenance WHERE lead_id = %s",
                [first["lead_id"]],
            )
            (count,) = cur.fetchone()
    finally:
        conn.close()
    assert count == 1

    provenance = _fetch_provenance(api_url, first["lead_id"])
    assert provenance is not None
    # The retry's different discovery_token must never overwrite the
    # original, already-persisted, immutable provenance row.
    assert provenance.discovery_surface is DiscoverySurface.UNKNOWN


# ---------------------------------------------------------------------------
# Existing Lead/notification invariants remain unchanged
# ---------------------------------------------------------------------------


def test_existing_invariants_unchanged_by_provenance_wiring(
    client: TestClient, api_url: str
) -> None:
    _publish_listing(api_url, listing_id="NLP9")
    body = _submit_contact(
        client,
        "NLP9",
        op_suffix="A",
        extra={"utm_source": "google", "utm_medium": "cpc"},
    )
    assert body["status"] == "CREATED"

    conn = psycopg.connect(api_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT contact_email_verification_state FROM buyer_leads WHERE lead_id = %s",
                [body["lead_id"]],
            )
            (verification_state,) = cur.fetchone()
            cur.execute(
                "SELECT COUNT(*) FROM lead_notification_outbox WHERE lead_id = %s",
                [body["lead_id"]],
            )
            (outbox_count,) = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM buyer_leads WHERE native_listing_id = %s", ["NLP9"])
            (lead_count,) = cur.fetchone()
    finally:
        conn.close()
    assert verification_state == "UNVERIFIED"
    assert outbox_count == 1
    assert lead_count == 1
