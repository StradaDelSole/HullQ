"""SLICE-0095 real-PostgreSQL genuinely concurrent-authorization/lifecycle
proofs for the Power broker Search-fit preview — mirrors
`test_broker_search_fit_concurrency.py`'s identical discipline (itself
established by the SLICE-0084 independent review Finding A, PR #342) for
the structurally separate
`hullq.application.power_broker_search_fit.evaluate_organization_listing_power_search_fit`.

`evaluate_organization_listing_power_search_fit` reads authorization,
lifecycle, the NativeListing -> MarketEpisode -> PhysicalBoat chain and
technical classification inside one `REPEATABLE READ` snapshot
transaction, then rechecks both authorization and lifecycle once more from
fresh statements immediately after that snapshot closes (see that module's
docstring). This module proves the *second* phase actually catches a real,
independent-connection mutation landing while the first phase's snapshot
read was in flight -- not merely that the two phases exist in source.
"""

from __future__ import annotations

import dataclasses
import threading
import uuid
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

import hullq.application.power_broker_search_fit as power_broker_search_fit
from hullq.application.power_broker_search_fit import (
    PowerSearchFitOutcome,
    evaluate_organization_listing_power_search_fit,
)
from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    PowerDriveConfiguration,
    PowerDriveConfigurationClaim,
    PowerEngineCountClaim,
    VesselCategory,
    VesselCategoryClaim,
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
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
    update_membership_state,
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    write_physical_boat_claim_revision,
)
from hullq.security.session_token import SessionClaims

_ORG_ID = "ORG-PSFCONC"
_ACCOUNT_ID = "ACC-PSFCONC"
_MEMBERSHIP_ID = "OM-PSFCONC"
_LISTING_ID = "NL-PSFCONC"
_PHYSICAL_BOAT_ID = "PB-PSFCONC"
_MARKET_EPISODE_ID = "ME-PSFCONC"

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
def conc_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0095conc_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


def _session() -> SessionClaims:
    now = datetime.now(UTC)
    return SessionClaims(
        account_id=AccountId(_ACCOUNT_ID),
        identity=AuthenticatedIdentity(
            provider=Provider.AUTH0,
            issuer="https://issuer.test/",
            subject=f"subject-{_ACCOUNT_ID}",
            auth_time=now,
            mfa_satisfied=True,
        ),
        issued_at=now,
        expires_at=now,
    )


def _seed_draft_listing_with_confirmed_match(conc_url: str) -> None:
    """One lifecycle-DRAFT, design-unresolved NativeListing with a confirmed
    POWER+SHAFT claim -- a request for `power_drive=SHAFT` against it
    resolves CONFIRMED_MATCH absent any race."""
    conn = psycopg.connect(conc_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [_ACCOUNT_ID],
            )
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(_ORG_ID),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        seed_marketplace_organization(conn, org)
        account = AccountId(_ACCOUNT_ID)
        membership = OrganizationMembership(
            id=OrganizationMembershipId(_MEMBERSHIP_ID),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        seed_organization_membership(conn, membership)
        conn.commit()

        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(id=PhysicalBoatId(_PHYSICAL_BOAT_ID), boat_design_ref=None),
        )
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(_MARKET_EPISODE_ID),
                physical_boat_id=PhysicalBoatId(_PHYSICAL_BOAT_ID),
            ),
        )
        create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(_LISTING_ID),
                market_episode_id=MarketEpisodeId(_MARKET_EPISODE_ID),
            ),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(_LISTING_ID),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-PSFCONC-1"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Swift Trawler 35",
                build_year=BuildYearClaim(assertion_kind=VA, value=2020),
                vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
                power_drive_configuration=PowerDriveConfigurationClaim(
                    assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
                ),
            ),
        )
    finally:
        conn.close()


def _run_with_paused_recheck(
    conc_url: str, *, between_snapshot_and_recheck: Callable[[], None]
) -> Any:
    """Call `evaluate_organization_listing_power_search_fit` on its own
    fresh connection, with the module's `_authorize_actor` patched so that
    its *second* call (the post-snapshot recheck) first invokes
    *between_snapshot_and_recheck* -- giving a concurrent mutator a
    deterministic window strictly between the snapshot read (already fully
    complete, including the *first* `_authorize_actor` call) and the
    recheck."""
    original_authorize = power_broker_search_fit._authorize_actor
    call_count = {"n": 0}

    def _patched(conn: Any, session: Any, organization_id: Any) -> Any:
        call_count["n"] += 1
        if call_count["n"] == 2:
            between_snapshot_and_recheck()
        return original_authorize(conn, session, organization_id)

    power_broker_search_fit._authorize_actor = _patched  # type: ignore[attr-defined]
    try:
        conn = psycopg.connect(conc_url)
        try:
            return evaluate_organization_listing_power_search_fit(
                conn,
                _session(),
                _ORG_ID,
                _LISTING_ID,
                {"power_drive": ["SHAFT"]},
                as_of=datetime.now(UTC),
            )
        finally:
            conn.close()
    finally:
        power_broker_search_fit._authorize_actor = original_authorize  # type: ignore[attr-defined]


def test_publisher_role_revoked_mid_evaluation_fails_closed(conc_url: str) -> None:
    """A PUBLISHER role removed strictly between the snapshot read and the
    post-snapshot recheck must be caught by the recheck -- never a stale
    OK built from an authorization decision that no longer holds."""
    _seed_draft_listing_with_confirmed_match(conc_url)

    proceed = threading.Event()
    mutated = threading.Event()

    def _revoke_publisher_role() -> None:
        mutator_conn = psycopg.connect(conc_url)
        try:
            seed_organization_membership(
                mutator_conn,
                OrganizationMembership(
                    id=OrganizationMembershipId(_MEMBERSHIP_ID),
                    account_id=AccountId(_ACCOUNT_ID),
                    organization_id=MarketplaceOrganizationId(_ORG_ID),
                    roles=frozenset(),  # PUBLISHER removed
                    state=MembershipState.ACTIVE,
                ),
            )
            mutator_conn.commit()
        finally:
            mutator_conn.close()
        mutated.set()
        proceed.wait(timeout=10)

    result_holder: list[Any] = []

    def _evaluate() -> None:
        def _pause_for_mutation() -> None:
            thread = threading.Thread(target=_revoke_publisher_role)
            thread.start()
            assert mutated.wait(timeout=10), "mutator did not commit in time"
            thread.join(timeout=10)

        result_holder.append(
            _run_with_paused_recheck(conc_url, between_snapshot_and_recheck=_pause_for_mutation)
        )
        proceed.set()

    eval_thread = threading.Thread(target=_evaluate)
    eval_thread.start()
    eval_thread.join(timeout=20)

    assert len(result_holder) == 1
    result = result_holder[0]
    assert result.outcome is PowerSearchFitOutcome.PUBLISHER_ROLE_REQUIRED, result


def test_membership_deactivated_mid_evaluation_fails_closed(conc_url: str) -> None:
    """A membership deactivated strictly between the snapshot read and the
    post-snapshot recheck must be caught, non-enumerating (same outcome as
    an unknown Organization)."""
    _seed_draft_listing_with_confirmed_match(conc_url)

    proceed = threading.Event()
    mutated = threading.Event()

    def _deactivate_membership() -> None:
        mutator_conn = psycopg.connect(conc_url)
        try:
            update_membership_state(
                mutator_conn, OrganizationMembershipId(_MEMBERSHIP_ID), MembershipState.INACTIVE
            )
            mutator_conn.commit()
        finally:
            mutator_conn.close()
        mutated.set()
        proceed.wait(timeout=10)

    result_holder: list[Any] = []

    def _evaluate() -> None:
        def _pause_for_mutation() -> None:
            thread = threading.Thread(target=_deactivate_membership)
            thread.start()
            assert mutated.wait(timeout=10), "mutator did not commit in time"
            thread.join(timeout=10)

        result_holder.append(
            _run_with_paused_recheck(conc_url, between_snapshot_and_recheck=_pause_for_mutation)
        )
        proceed.set()

    eval_thread = threading.Thread(target=_evaluate)
    eval_thread.start()
    eval_thread.join(timeout=20)

    assert len(result_holder) == 1
    result = result_holder[0]
    assert result.outcome is PowerSearchFitOutcome.ORG_NOT_FOUND_OR_DENIED, result


def test_lifecycle_published_mid_evaluation_fails_closed(conc_url: str) -> None:
    """A NativeListing published (DRAFT -> ACTIVE) strictly between the
    snapshot read and the post-snapshot recheck must report
    `NOT_PREVIEWABLE` -- never a DRAFT-labelled preview assembled from a
    state moment the listing has since moved past."""
    _seed_draft_listing_with_confirmed_match(conc_url)

    proceed = threading.Event()
    mutated = threading.Event()

    def _force_active() -> None:
        mutator_conn = psycopg.connect(conc_url)
        try:
            with mutator_conn.cursor() as cur:
                cur.execute(
                    "UPDATE native_listings SET lifecycle_state = 'ACTIVE' "
                    "WHERE native_listing_id = %s",
                    [_LISTING_ID],
                )
            mutator_conn.commit()
        finally:
            mutator_conn.close()
        mutated.set()
        proceed.wait(timeout=10)

    result_holder: list[Any] = []

    def _evaluate() -> None:
        def _pause_for_mutation() -> None:
            thread = threading.Thread(target=_force_active)
            thread.start()
            assert mutated.wait(timeout=10), "mutator did not commit in time"
            thread.join(timeout=10)

        result_holder.append(
            _run_with_paused_recheck(conc_url, between_snapshot_and_recheck=_pause_for_mutation)
        )
        proceed.set()

    eval_thread = threading.Thread(target=_evaluate)
    eval_thread.start()
    eval_thread.join(timeout=20)

    assert len(result_holder) == 1
    result = result_holder[0]
    assert result.outcome is PowerSearchFitOutcome.NOT_PREVIEWABLE, result


def test_listing_ownership_disagreement_on_recheck_fails_closed(conc_url: str) -> None:
    """Independent review amendment Finding C (round 1): the post-snapshot
    recheck must independently re-verify the NativeListing's
    `publishing_organization_id`, not only lifecycle -- the contract's own
    words are "independently recheck current role/MFA authorization and
    listing ownership/lifecycle with fresh statements".

    No accepted persistence write path in this codebase can ever actually
    reassign a NativeListing's `publishing_organization_id` after creation
    (`hullq.persistence.native_listing` issues no such `UPDATE`; the only
    mutable column on `native_listings` is `lifecycle_state`, via
    `hullq.persistence.native_listing_lifecycle._apply_transition`) -- so a
    genuine two-connection ownership-transfer race cannot be constructed
    through any accepted write path, and none is claimed here. This test
    instead proves the new recheck's own fail-closed *code path*
    deterministically against a real PostgreSQL-backed evaluation: every
    read is genuine except the recheck's own second call to
    `fetch_native_listing`, which is forced to observe a foreign-owned
    record (the snapshot's own first call, and every other read, is left
    completely unpatched). The result must still collapse to the identical
    non-enumerating `LISTING_NOT_FOUND` the snapshot phase itself already
    uses for the same condition -- never a stale OK.
    """
    _seed_draft_listing_with_confirmed_match(conc_url)

    original_fetch = power_broker_search_fit.fetch_native_listing
    call_count = {"n": 0}

    def _patched_fetch(conn: Any, native_listing_id: Any) -> Any:
        call_count["n"] += 1
        record = original_fetch(conn, native_listing_id)
        if call_count["n"] >= 2 and record is not None:
            return dataclasses.replace(
                record,
                publishing_organization_id=MarketplaceOrganizationId("ORG-PSFCONC-FOREIGN"),
            )
        return record

    power_broker_search_fit.fetch_native_listing = _patched_fetch  # type: ignore[attr-defined]
    try:
        conn = psycopg.connect(conc_url)
        try:
            result = evaluate_organization_listing_power_search_fit(
                conn,
                _session(),
                _ORG_ID,
                _LISTING_ID,
                {"power_drive": ["SHAFT"]},
                as_of=datetime.now(UTC),
            )
        finally:
            conn.close()
    finally:
        power_broker_search_fit.fetch_native_listing = original_fetch  # type: ignore[attr-defined]

    assert result.outcome is PowerSearchFitOutcome.LISTING_NOT_FOUND, result


_COMBINED_LISTING_ID = "NL-PSFCONC-COMBINED"
_COMBINED_PHYSICAL_BOAT_ID = "PB-PSFCONC-COMBINED"
_COMBINED_MARKET_EPISODE_ID = "ME-PSFCONC-COMBINED"


def _seed_draft_listing_with_confirmed_combined_match(conc_url: str) -> None:
    """One lifecycle-DRAFT, design-unresolved NativeListing with a
    confirmed POWER+SHAFT+count=2 claim -- a combined
    `power_drive=SHAFT&power_engine_count=2` request against it resolves
    CONFIRMED_MATCH absent any race."""
    conn = psycopg.connect(conc_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [_ACCOUNT_ID],
            )
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(_ORG_ID),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        seed_marketplace_organization(conn, org)
        account = AccountId(_ACCOUNT_ID)
        membership = OrganizationMembership(
            id=OrganizationMembershipId(_MEMBERSHIP_ID),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        seed_organization_membership(conn, membership)
        conn.commit()

        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(_COMBINED_PHYSICAL_BOAT_ID), boat_design_ref=None
            ),
        )
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(_COMBINED_MARKET_EPISODE_ID),
                physical_boat_id=PhysicalBoatId(_COMBINED_PHYSICAL_BOAT_ID),
            ),
        )
        create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(_COMBINED_LISTING_ID),
                market_episode_id=MarketEpisodeId(_COMBINED_MARKET_EPISODE_ID),
            ),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(_COMBINED_LISTING_ID),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-PSFCONC-COMBINED-1"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Swift Trawler 35",
                build_year=BuildYearClaim(assertion_kind=VA, value=2020),
                vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
                power_drive_configuration=PowerDriveConfigurationClaim(
                    assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
                ),
                power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
            ),
        )
    finally:
        conn.close()


def test_category_drive_count_revision_mid_evaluation_reflects_consistent_pre_mutation_snapshot(
    conc_url: str,
) -> None:
    """Independent review amendment Finding D (round 1): a real
    two-connection concurrent category+drive+count claim revision race,
    invoking the NEW private evaluator directly -- mirrors
    `test_broker_search_fit_concurrency.py
    .test_claim_changed_mid_evaluation_reflects_consistent_pre_mutation_snapshot`'s
    identical discipline, generalized from a single Sail field to all
    three Power fields at once (category, drive AND count changed in one
    concurrently-committed revision).

    A concrete PhysicalBoat claim revision changing category (POWER ->
    SAIL), drive (SHAFT -> OUTBOARD) AND count (2 -> 5) all at once,
    committed strictly between the snapshot read and the post-snapshot
    recheck, must never produce a torn/hybrid result: the returned
    evidence must reflect the exact pre-mutation revision the
    `REPEATABLE READ` snapshot actually read (a genuine combined
    CONFIRMED_MATCH on SHAFT+2), even though a fresh read after that
    snapshot would see an entirely different, SAIL-excluded revision.
    Never a hybrid combining the old category admission with the new
    drive/count values, or vice versa."""
    _seed_draft_listing_with_confirmed_combined_match(conc_url)

    proceed = threading.Event()
    mutated = threading.Event()

    def _mutate_category_drive_count() -> None:
        mutator_conn = psycopg.connect(conc_url)
        try:
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership = OrganizationMembership(
                id=OrganizationMembershipId(_MEMBERSHIP_ID),
                account_id=AccountId(_ACCOUNT_ID),
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            current = fetch_current_physical_boat_claim(
                mutator_conn, PhysicalBoatId(_COMBINED_PHYSICAL_BOAT_ID), org.id
            )
            assert current is not None
            mutator_conn.commit()
            write_physical_boat_claim_revision(
                mutator_conn,
                account_id=AccountId(_ACCOUNT_ID),
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_COMBINED_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-PSFCONC-COMBINED-2"),
                expected_current_revision_id=current.revision_id,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Swift Trawler 35",
                    build_year=BuildYearClaim(assertion_kind=VA, value=2020),
                    vessel_category=VesselCategoryClaim(
                        assertion_kind=VA, value=VesselCategory.SAIL
                    ),
                    power_drive_configuration=PowerDriveConfigurationClaim(
                        assertion_kind=VA, value=PowerDriveConfiguration.OUTBOARD
                    ),
                    power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=5),
                ),
            )
        finally:
            mutator_conn.close()
        mutated.set()
        proceed.wait(timeout=10)

    result_holder: list[Any] = []

    def _evaluate() -> None:
        def _pause_for_mutation() -> None:
            thread = threading.Thread(target=_mutate_category_drive_count)
            thread.start()
            assert mutated.wait(timeout=10), "mutator did not commit in time"
            thread.join(timeout=10)

        original_authorize = power_broker_search_fit._authorize_actor
        call_count = {"n": 0}

        def _patched(conn: Any, session: Any, organization_id: Any) -> Any:
            call_count["n"] += 1
            if call_count["n"] == 2:
                _pause_for_mutation()
            return original_authorize(conn, session, organization_id)

        power_broker_search_fit._authorize_actor = _patched  # type: ignore[attr-defined]
        try:
            conn = psycopg.connect(conc_url)
            try:
                result_holder.append(
                    evaluate_organization_listing_power_search_fit(
                        conn,
                        _session(),
                        _ORG_ID,
                        _COMBINED_LISTING_ID,
                        {"power_drive": ["SHAFT"], "power_engine_count": ["2"]},
                        as_of=datetime.now(UTC),
                    )
                )
            finally:
                conn.close()
        finally:
            power_broker_search_fit._authorize_actor = original_authorize  # type: ignore[attr-defined]
        proceed.set()

    eval_thread = threading.Thread(target=_evaluate)
    eval_thread.start()
    eval_thread.join(timeout=20)

    assert len(result_holder) == 1
    result = result_holder[0]
    # The snapshot read the pre-mutation revision (POWER+SHAFT+2,
    # CONFIRMED_MATCH), never the concurrently-committed SAIL+OUTBOARD+5 --
    # proving the REPEATABLE READ snapshot held across the whole
    # evaluation, including every one of the three fields changed at once.
    assert result.outcome is PowerSearchFitOutcome.OK, result
    assert result.view is not None
    assert result.view.result_class.value == "CONFIRMED_MATCH", result.view
    assert result.view.vessel_category_exclusion is None
    drive_evidence = next(
        e
        for e in result.view.criterion_evidence
        if e.criterion.field == "power_drive_configuration"
    )
    count_evidence = next(
        e for e in result.view.criterion_evidence if e.criterion.field == "power_engine_count"
    )
    assert drive_evidence.observed_value == "SHAFT"
    assert count_evidence.observed_value == 2

    verify_conn = psycopg.connect(conc_url)
    try:
        current_claim_after = fetch_current_physical_boat_claim(
            verify_conn,
            PhysicalBoatId(_COMBINED_PHYSICAL_BOAT_ID),
            MarketplaceOrganizationId(_ORG_ID),
        )
    finally:
        verify_conn.close()
    # The mutation genuinely committed and is now the real current claim --
    # the preview's own consistent-but-older read never rewrote anything.
    assert current_claim_after is not None
    assert current_claim_after.claims.vessel_category is not None
    assert current_claim_after.claims.vessel_category.value == VesselCategory.SAIL
    assert current_claim_after.claims.power_drive_configuration is not None
    assert (
        current_claim_after.claims.power_drive_configuration.value
        == PowerDriveConfiguration.OUTBOARD
    )
    assert current_claim_after.claims.power_engine_count is not None
    assert current_claim_after.claims.power_engine_count.value == 5
