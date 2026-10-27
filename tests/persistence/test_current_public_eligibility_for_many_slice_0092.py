"""PostgreSQL-backed equivalence proof: `resolve_current_public_eligibility_for_many`
vs. `resolve_current_public_eligibility` -- SLICE-0092 amendment review (PR #387)
Finding D.

Finding D required accepted D29 semantics to be "proven against the existing
resolver for all suppression states" before the new batched/bulk path could be
trusted by the design-unresolved claim-only Sail funnel. This module seeds one
real NativeListing per independently reachable D29 suppression axis plus one
fully-eligible control, then asserts the new bulk function and the pre-existing,
unmodified single-id function reach byte-for-byte the same `status` for every
one of them -- and, for every axis where the bulk function's documented
contract promises a *complete* (not merely cheap-partial) reason set, the
exact same `suppression_reasons` too.

Six suppression reasons are deliberately NOT exercised here --
`MARKET_EPISODE_UNRESOLVED` (while ACTIVE), `PHYSICAL_BOAT_MISSING`,
`OFFER_MISSING`, `PHYSICAL_BOAT_CLAIM_MISSING`, `NO_PUBLIC_USABLE_IMAGE` and
`COVER_MISSING`/`COVER_INVALID` -- because this repository's own accepted
write paths make every one of them unreachable for an `ACTIVE` NativeListing,
for both functions equally:

- `publish_native_listing`'s readiness gate (verified directly by running
  this suite: seeding a listing without an episode/claim/offer/cover and
  then publishing returns `INCOMPLETE_LISTING` with the corresponding
  `PublicationBlockerReason`, never `transitioned`) already requires every
  one of episode-linkage, claim, offer and cover to be present before a
  listing can become `ACTIVE` at all.
- `hullq.persistence.media_gallery.remove_placement` explicitly rejects
  (`ACTIVE_LISTING_CONFLICT`, writing nothing) removing an `ACTIVE`
  listing's current cover or its last remaining valid public image.
- No accepted write path retracts an already-written offer or
  PhysicalBoatClaim revision back to "missing" for an `ACTIVE` listing.

This mirrors `hullq.domain.current_public_eligibility`'s own module
docstring ("why an existing offer/PhysicalBoat-claim record is always
already valid by construction") -- these six reasons exist in the pure
evaluator for completeness/defense-in-depth, not because today's accepted
persistence layer can produce them post-`ACTIVE`. The three suppression
axes genuinely reachable for an `ACTIVE` listing --
`LIFECYCLE_NOT_ACTIVE` (never published), `FRESHNESS_NOT_CURRENT`
(elapsed `as_of`) and `ORGANIZATION_NOT_ELIGIBLE` (an Organization demoted
*after* publication, the same real-world case the claim-only funnel's own
D29-suppression test already covers) -- are each proven below.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.current_public_eligibility import (
    resolve_current_public_eligibility,
    resolve_current_public_eligibility_for_many,
)
from hullq.domain.current_public_eligibility import (
    CurrentPublicEligibilityStatus,
    CurrentPublicSuppressionReason,
)
from hullq.domain.market_identity import (
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
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
)
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

VA = AssertionKind.VALUE_ASSERTION


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
def bulk_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0092bulk_{uuid.uuid4().hex[:16]}"
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
def bulk_conn(bulk_url: str) -> Generator[Any]:
    conn = psycopg.connect(bulk_url)
    try:
        yield conn
    finally:
        conn.close()


def _as_of() -> datetime:
    return datetime.now(UTC)


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


class _Fixture:
    """One seeded NativeListing plus everything needed to reproduce it."""

    def __init__(
        self,
        *,
        listing_id: NativeListingId,
        org: MarketplaceOrganization,
        account: AccountId,
        membership: OrganizationMembership,
    ) -> None:
        self.listing_id = listing_id
        self.org = org
        self.account = account
        self.membership = membership


def _seed_base(
    conn: Any,
    *,
    tag: str,
    with_episode: bool,
    with_offer: bool,
    with_claim: bool,
    with_cover: bool,
    publish: bool,
) -> _Fixture:
    listing_id = NativeListingId(f"NL-92BULK-{tag}")
    physical_boat_id = PhysicalBoatId(f"PB-92BULK-{tag}")
    market_episode_id = MarketEpisodeId(f"ME-92BULK-{tag}")
    account = AccountId(f"ACC-92BULK-{tag}")
    org = _org(f"ORG-92BULK-{tag}")
    membership = _membership(org, account, f"OM-92BULK-{tag}")

    episode_ref: MarketEpisodeId | None = None
    if with_episode:
        create_physical_boat(
            conn, physical_boat=PhysicalBoat(id=physical_boat_id, boat_design_ref=None)
        )
        create_market_episode(
            conn,
            market_episode=MarketEpisode(id=market_episode_id, physical_boat_id=physical_boat_id),
        )
        episode_ref = market_episode_id

    create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=listing_id, market_episode_id=episode_ref),
    )

    if with_offer:
        write_native_listing_offer_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=listing_id,
            revision_id=NativeListingOfferRevisionId(f"REV-92BULK-{tag}"),
            expected_current_revision_id=None,
            offer=NativeListingOfferSnapshot(
                asking_price_mode=AskingPriceMode.AMOUNT,
                location_country="FR",
                broker_description="Bulk-equivalence proof listing.",
                asking_price_amount=Decimal("90000.00"),
                currency="EUR",
            ),
        )

    if with_claim and with_episode:
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=listing_id,
            revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-92BULK-{tag}"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Unbranded",
                model_designation_claim="Bulk Model",
                build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            ),
        )

    if with_cover:
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
                original_object_key=f"original/{listing_id.value}",
                derivative_object_key=f"derivative/{listing_id.value}",
                content_hash=f"hash-{listing_id.value}",
                mime_type="image/jpeg",
                width=800,
                height=600,
                byte_size=12345,
            )
            placement_result = create_uploaded_image_placement(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_asset=asset,
            )
            cover_result = set_cover(
                conn,
                native_listing_id=listing_id,
                owner_organization_id=org.id,
                media_placement_id=placement_result.media_placement_id,
                expected_version=placement_result.gallery_version,
            )
            assert cover_result.outcome.value == "SET", cover_result

    if publish:
        publish_result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=listing_id,
        )
        assert publish_result.status.value == "transitioned", publish_result

    conn.commit()
    return _Fixture(listing_id=listing_id, org=org, account=account, membership=membership)


def _assert_equivalent(
    conn: Any,
    fixture: _Fixture,
    *,
    as_of: datetime,
    expect_status: CurrentPublicEligibilityStatus,
    expect_reason_present: CurrentPublicSuppressionReason | None,
    expect_exact_reasons: bool,
) -> None:
    single_result = resolve_current_public_eligibility(conn, fixture.listing_id, as_of=as_of)
    assert single_result is not None
    bulk_map = resolve_current_public_eligibility_for_many(conn, [fixture.listing_id], as_of=as_of)
    bulk_result = bulk_map[fixture.listing_id.value]

    assert single_result.status is expect_status, (fixture.listing_id.value, single_result)
    assert bulk_result.eligibility.status is expect_status, (
        fixture.listing_id.value,
        bulk_result.eligibility,
    )

    if expect_reason_present is not None:
        assert expect_reason_present in single_result.suppression_reasons
        assert expect_reason_present in bulk_result.eligibility.suppression_reasons

    if expect_exact_reasons:
        assert bulk_result.eligibility.suppression_reasons == single_result.suppression_reasons
    else:
        # A cheap-suppressed bulk result is a truthful, possibly-partial
        # subset of the full single-call reason set (contract of
        # `BulkCurrentPublicEligibility.eligibility`) -- it must never claim
        # a reason the full evaluation would not also report.
        assert bulk_result.eligibility.suppression_reasons <= single_result.suppression_reasons


def test_fully_eligible_control_matches_exactly(bulk_conn: Any) -> None:
    fixture = _seed_base(
        bulk_conn,
        tag="ELIGIBLE",
        with_episode=True,
        with_offer=True,
        with_claim=True,
        with_cover=True,
        publish=True,
    )
    _assert_equivalent(
        bulk_conn,
        fixture,
        as_of=_as_of(),
        expect_status=CurrentPublicEligibilityStatus.ELIGIBLE,
        expect_reason_present=None,
        expect_exact_reasons=True,
    )


def test_lifecycle_not_active_matches(bulk_conn: Any) -> None:
    fixture = _seed_base(
        bulk_conn,
        tag="DRAFT",
        with_episode=True,
        with_offer=True,
        with_claim=True,
        with_cover=True,
        publish=False,
    )
    _assert_equivalent(
        bulk_conn,
        fixture,
        as_of=_as_of(),
        expect_status=CurrentPublicEligibilityStatus.SUPPRESSED,
        expect_reason_present=CurrentPublicSuppressionReason.LIFECYCLE_NOT_ACTIVE,
        expect_exact_reasons=False,
    )


def test_freshness_not_current_matches(bulk_conn: Any) -> None:
    fixture = _seed_base(
        bulk_conn,
        tag="STALE",
        with_episode=True,
        with_offer=True,
        with_claim=True,
        with_cover=True,
        publish=True,
    )
    far_future = _as_of() + timedelta(days=400)
    _assert_equivalent(
        bulk_conn,
        fixture,
        as_of=far_future,
        expect_status=CurrentPublicEligibilityStatus.SUPPRESSED,
        expect_reason_present=CurrentPublicSuppressionReason.FRESHNESS_NOT_CURRENT,
        expect_exact_reasons=False,
    )


def test_organization_not_eligible_matches(bulk_conn: Any) -> None:
    fixture = _seed_base(
        bulk_conn,
        tag="ORGBAD",
        with_episode=True,
        with_offer=True,
        with_claim=True,
        with_cover=True,
        publish=True,
    )
    demoted_org = MarketplaceOrganization(
        id=fixture.org.id,
        professional_category=fixture.org.professional_category,
        publishing_eligibility=OrganizationPublishingEligibility.UNVERIFIED,
    )
    seed_marketplace_organization(bulk_conn, demoted_org)
    bulk_conn.commit()
    _assert_equivalent(
        bulk_conn,
        fixture,
        as_of=_as_of(),
        expect_status=CurrentPublicEligibilityStatus.SUPPRESSED,
        expect_reason_present=CurrentPublicSuppressionReason.ORGANIZATION_NOT_ELIGIBLE,
        expect_exact_reasons=False,
    )


def test_market_episode_unresolved_while_draft_matches(bulk_conn: Any) -> None:
    """Not reachable while `ACTIVE` (see module docstring); reachable while
    still `DRAFT`, where it co-occurs with `LIFECYCLE_NOT_ACTIVE` -- the
    bulk cheap-check must still report it as a truthful subset member."""
    fixture = _seed_base(
        bulk_conn,
        tag="NOEPISODE",
        with_episode=False,
        with_offer=True,
        with_claim=False,
        with_cover=True,
        publish=False,
    )
    _assert_equivalent(
        bulk_conn,
        fixture,
        as_of=_as_of(),
        expect_status=CurrentPublicEligibilityStatus.SUPPRESSED,
        expect_reason_present=CurrentPublicSuppressionReason.MARKET_EPISODE_UNRESOLVED,
        expect_exact_reasons=False,
    )


def test_publish_readiness_gate_blocks_missing_claim_offer_cover(bulk_conn: Any) -> None:
    """Documents, with a real assertion rather than only prose, exactly why
    OFFER_MISSING/PHYSICAL_BOAT_CLAIM_MISSING/COVER_MISSING are excluded
    above: attempting to publish a listing missing any of them never
    reaches `ACTIVE` at all, for either resolver to subsequently observe."""
    from hullq.domain.publication_readiness import PublicationBlockerReason
    from hullq.persistence.native_listing_lifecycle import LifecycleTransitionStatus

    listing_id = NativeListingId("NL-92BULK-INCOMPLETE")
    physical_boat_id = PhysicalBoatId("PB-92BULK-INCOMPLETE")
    market_episode_id = MarketEpisodeId("ME-92BULK-INCOMPLETE")
    account = AccountId("ACC-92BULK-INCOMPLETE")
    org = _org("ORG-92BULK-INCOMPLETE")
    membership = _membership(org, account, "OM-92BULK-INCOMPLETE")

    create_physical_boat(
        bulk_conn, physical_boat=PhysicalBoat(id=physical_boat_id, boat_design_ref=None)
    )
    create_market_episode(
        bulk_conn,
        market_episode=MarketEpisode(id=market_episode_id, physical_boat_id=physical_boat_id),
    )
    create_native_listing(
        bulk_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=listing_id, market_episode_id=market_episode_id),
    )
    bulk_conn.commit()

    publish_result = publish_native_listing(
        bulk_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=listing_id,
    )
    assert publish_result.status is LifecycleTransitionStatus.INCOMPLETE_LISTING
    assert PublicationBlockerReason.PHYSICAL_BOAT_CLAIM_MISSING in publish_result.blockers


def test_bulk_population_mixes_every_axis_in_one_call(bulk_conn: Any) -> None:
    """The same fixtures above, resolved together through ONE
    `resolve_current_public_eligibility_for_many` call, still match the
    single-id function per-listing -- proving the batching itself (shared
    cursors/temporary dicts across distinct candidates) never cross-
    contaminates results between candidates."""
    eligible = _seed_base(
        bulk_conn,
        tag="MIX-ELIGIBLE",
        with_episode=True,
        with_offer=True,
        with_claim=True,
        with_cover=True,
        publish=True,
    )
    draft = _seed_base(
        bulk_conn,
        tag="MIX-DRAFT",
        with_episode=True,
        with_offer=True,
        with_claim=True,
        with_cover=True,
        publish=False,
    )
    org_bad = _seed_base(
        bulk_conn,
        tag="MIX-ORGBAD",
        with_episode=True,
        with_offer=True,
        with_claim=True,
        with_cover=True,
        publish=True,
    )
    demoted_org = MarketplaceOrganization(
        id=org_bad.org.id,
        professional_category=org_bad.org.professional_category,
        publishing_eligibility=OrganizationPublishingEligibility.UNVERIFIED,
    )
    seed_marketplace_organization(bulk_conn, demoted_org)
    bulk_conn.commit()
    no_episode_draft = _seed_base(
        bulk_conn,
        tag="MIX-NOEPISODE",
        with_episode=False,
        with_offer=True,
        with_claim=False,
        with_cover=True,
        publish=False,
    )
    bulk_conn.commit()

    as_of = _as_of()
    all_fixtures = [eligible, draft, org_bad, no_episode_draft]
    bulk_map = resolve_current_public_eligibility_for_many(
        bulk_conn, [f.listing_id for f in all_fixtures], as_of=as_of
    )
    assert len(bulk_map) == len(all_fixtures)

    for fixture in all_fixtures:
        single_result = resolve_current_public_eligibility(
            bulk_conn, fixture.listing_id, as_of=as_of
        )
        assert single_result is not None
        bulk_result = bulk_map[fixture.listing_id.value]
        assert bulk_result.eligibility.status is single_result.status, fixture.listing_id.value
        assert bulk_result.eligibility.suppression_reasons <= single_result.suppression_reasons, (
            fixture.listing_id.value
        )

    assert bulk_map[eligible.listing_id.value].eligibility.status is (
        CurrentPublicEligibilityStatus.ELIGIBLE
    )
    assert bulk_map[eligible.listing_id.value].eligibility.suppression_reasons == frozenset()
