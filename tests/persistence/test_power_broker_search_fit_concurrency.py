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
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
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
            conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(_PHYSICAL_BOAT_ID), boat_design_ref=None)
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
