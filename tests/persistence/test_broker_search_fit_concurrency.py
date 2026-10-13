"""SLICE-0084 real-PostgreSQL genuinely concurrent-authorization/lifecycle
proofs — independent review Finding A (PR #342, review 5504494678).

`hullq.application.broker_search_fit.evaluate_organization_listing_search_fit`
reads authorization, lifecycle, the NativeListing -> MarketEpisode ->
PhysicalBoat chain, design evaluation and concrete claim classification
inside one `REPEATABLE READ` snapshot transaction, then rechecks both
authorization and lifecycle once more from fresh statements immediately
after that snapshot closes (see that module's docstring). This module
proves the *second* phase actually catches a real, independent-connection
mutation landing while the first phase's snapshot read was in flight --
not merely that the two phases exist in source.

Mirrors `test_inventory_editing_concurrency.py`'s genuinely-concurrent,
independent-psycopg-connection discipline, but the race here is read-then-
recheck rather than two competing writes serialized by a row lock, so the
synchronization primitive is different: `evaluate_organization_listing_
search_fit`'s own module-level `_authorize_actor` is monkeypatched so its
*second* call (the post-snapshot recheck -- the first call, inside the
snapshot, is left completely unpatched) blocks on a `threading.Event` until
a second, independent connection has committed its mutation. This proves
the exact mechanism the review required: an authorization/lifecycle change
committed strictly *between* the snapshot read and the recheck is observed
by the recheck, not hidden from it and not raced against it.
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

import hullq.application.broker_search_fit as broker_search_fit
from hullq.application.broker_search_fit import (
    SearchFitOutcome,
    evaluate_organization_listing_search_fit,
)
from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.market_identity import (
    BoatDesignRef,
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
    DraftClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
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
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
    update_membership_state,
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    write_physical_boat_claim_revision,
)
from hullq.search.draft_max_design_bridge import DRAFT_MAX_FIELD_POINTER
from hullq.search.keel_design_bridge import KEEL_TYPE_FIELD_POINTER, lookup_keel_canonical_value
from hullq.security.session_token import SessionClaims

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

_ORG_ID = "ORG-SFCONC"
_ACCOUNT_ID = "ACC-SFCONC"
_MEMBERSHIP_ID = "OM-SFCONC"
_LISTING_ID = "NL-SFCONC"
_PHYSICAL_BOAT_ID = "PB-SFCONC"
_MARKET_EPISODE_ID = "ME-SFCONC"
_DESIGN_ID = "BD-SFCONC"
_MODEL_ID = "BM-SFCONC"


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
    schema_name = f"hullq_s0084conc_{uuid.uuid4().hex[:16]}"
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
    """One lifecycle-DRAFT, design-linked NativeListing with a confirmed
    draft/keel claim -- a request for `draft_max=1.5&keel_configuration=FIN`
    against it resolves CONFIRMED_MATCH absent any race."""
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

        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
                "VALUES (%s, %s, %s)",
                [_MODEL_ID, "Model", "0" * 64],
            )
            baseline_json = json.dumps(
                {"dimensions": {"draft_max_m": 1.30}, "appendages": {"keel_type": "fin"}}
            )
            cur.execute(
                "INSERT INTO canonical_boat_designs "
                "(id, boat_model_id, generation, designers, baseline, named_variants, "
                " design_options, quality, content_hash) "
                "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
                "'[]'::jsonb, '{}'::jsonb, %s)",
                [_DESIGN_ID, _MODEL_ID, baseline_json, "1" * 64],
            )
        conn.commit()

        admit_resolved_draft_max(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=_DESIGN_ID,
            field_pointer=DRAFT_MAX_FIELD_POINTER,
            value=Decimal("1.30"),
            resolution_id=f"FR-DRAFT-{_DESIGN_ID}",
        )
        admit_resolved_categorical_field(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=_DESIGN_ID,
            field_pointer=KEEL_TYPE_FIELD_POINTER,
            value="fin",
            resolution_id=f"FR-KEEL-{_DESIGN_ID}",
            fetch_canonical_value=lookup_keel_canonical_value,
        )

        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(_PHYSICAL_BOAT_ID), boat_design_ref=BoatDesignRef(_DESIGN_ID)
            ),
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
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-SFCONC-1"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Oceanis 30.1",
                build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
                draft=DraftClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.20")
                ),
                keel_configuration=KeelConfigurationClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
                ),
            ),
        )
    finally:
        conn.close()


def _run_with_paused_recheck(
    conc_url: str, *, between_snapshot_and_recheck: Callable[[], None]
) -> Any:
    """Call `evaluate_organization_listing_search_fit` on its own fresh
    connection, with the module's `_authorize_actor` patched so that its
    *second* call (the post-snapshot recheck) first invokes
    *between_snapshot_and_recheck* -- giving a concurrent mutator a
    deterministic window strictly between the snapshot read (already fully
    complete, including the *first* `_authorize_actor` call) and the
    recheck. The first call is left completely unpatched, so the snapshot
    read itself is never affected."""
    original_authorize = broker_search_fit._authorize_actor
    call_count = {"n": 0}

    def _patched(conn: Any, session: Any, organization_id: Any) -> Any:
        call_count["n"] += 1
        if call_count["n"] == 2:
            between_snapshot_and_recheck()
        return original_authorize(conn, session, organization_id)

    broker_search_fit._authorize_actor = _patched  # type: ignore[attr-defined]
    try:
        conn = psycopg.connect(conc_url)
        try:
            return evaluate_organization_listing_search_fit(
                conn,
                _session(),
                _ORG_ID,
                _LISTING_ID,
                {"draft_max": ["1.5"], "keel_configuration": ["FIN"]},
                as_of=datetime.now(UTC),
            )
        finally:
            conn.close()
    finally:
        broker_search_fit._authorize_actor = original_authorize  # type: ignore[attr-defined]


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
    assert result.outcome is SearchFitOutcome.PUBLISHER_ROLE_REQUIRED, result


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
    assert result.outcome is SearchFitOutcome.ORG_NOT_FOUND_OR_DENIED, result


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
    assert result.outcome is SearchFitOutcome.NOT_PREVIEWABLE, result


def test_claim_changed_mid_evaluation_reflects_consistent_pre_mutation_snapshot(
    conc_url: str,
) -> None:
    """A concrete PhysicalBoat claim edited strictly between the snapshot
    read and the post-snapshot recheck must never produce a torn result:
    the returned evidence must reflect the exact pre-mutation claim the
    `REPEATABLE READ` snapshot actually read, even though a fresh read
    after that snapshot would see the new value. (Unlike role/lifecycle,
    an ordinary claim edit does not itself invalidate the preview --
    Required Behavior §C only requires authorization/lifecycle rechecking
    -- so this proves snapshot consistency, not a third recheck.)"""
    _seed_draft_listing_with_confirmed_match(conc_url)

    proceed = threading.Event()
    mutated = threading.Event()

    def _mutate_claim() -> None:
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
                mutator_conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), org.id
            )
            assert current is not None
            mutator_conn.commit()
            write_physical_boat_claim_revision(
                mutator_conn,
                account_id=AccountId(_ACCOUNT_ID),
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-SFCONC-2"),
                expected_current_revision_id=current.revision_id,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    draft=DraftClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.90")
                    ),
                    keel_configuration=KeelConfigurationClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
                    ),
                ),
            )
        finally:
            mutator_conn.close()
        mutated.set()
        proceed.wait(timeout=10)

    result_holder: list[Any] = []

    def _evaluate() -> None:
        def _pause_for_mutation() -> None:
            thread = threading.Thread(target=_mutate_claim)
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
    # The snapshot read the pre-mutation draft (1.20, CONFIRMED_MATCH),
    # never the concurrently-committed 1.90 -- proving the REPEATABLE READ
    # snapshot held across the whole evaluation, not merely across its own
    # first statement.
    assert result.outcome is SearchFitOutcome.OK, result
    assert result.view is not None
    assert result.view.result_class.value == "CONFIRMED_MATCH"
    draft_evidence = next(
        e for e in result.view.concrete_criterion_evidence if e.criterion.field == "draft_max_m"
    )
    assert draft_evidence.observed_value == Decimal("1.20")

    verify_conn = psycopg.connect(conc_url)
    try:
        lifecycle_after = fetch_lifecycle_state(verify_conn, NativeListingId(_LISTING_ID))
        current_claim_after = fetch_current_physical_boat_claim(
            verify_conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), MarketplaceOrganizationId(_ORG_ID)
        )
    finally:
        verify_conn.close()
    assert lifecycle_after is not None and lifecycle_after.value == "DRAFT"
    # The mutation genuinely committed and is now the real current claim --
    # the preview's own consistent-but-older read never rewrote anything.
    assert current_claim_after is not None
    assert current_claim_after.claims.draft is not None
    assert current_claim_after.claims.draft.value == Decimal("1.90")
