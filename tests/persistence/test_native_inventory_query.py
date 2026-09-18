"""PostgreSQL-backed end-to-end tests for the SLICE-0055 mixed native
inventory Search funnel (`hullq.application.native_inventory_query`).

Mirrors `tests/persistence/test_inventory_search_classification.py`'s
end-to-end shape (real FieldResolution-admitted design eligibility -> ACTIVE
native inventory admission -> concrete PhysicalBoat claim classification) but
exercises `keel_configuration` alone and combined with `draft_max`, proving
the slice's acceptance criteria: keel-only match/non-match/insufficient,
mixed joint match, draft TRUE + keel FALSE/UNKNOWN combinations, the
same-PhysicalBoat cross-Organization keel contradiction guard, an unsupported
BoatDesign taxonomy mapping failing closed while preserving design-side
evidence, missing/unresolved design-side keel truth likewise preserved, and
full typed evidence (requested criterion, typed truth/reason, safely
observed value, resolved configuration identity) retained for all three
result classes -- amendment Finding 1.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.native_inventory_query import evaluate_native_inventory_requirements
from hullq.domain.market_identity import (
    BoatDesignRef,
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
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
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.search.draft_max_design_bridge import DRAFT_MAX_FIELD_POINTER
from hullq.search.keel_design_bridge import (
    KEEL_TYPE_FIELD_POINTER,
    KEEL_TYPE_OVERRIDE_FIELD_POINTER,
    lookup_keel_canonical_value,
)
from hullq.search.types import ResultClass

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

# ---------------------------------------------------------------------------
# Disposable-schema fixture (mirrors test_inventory_search_classification.py)
# ---------------------------------------------------------------------------


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
    schema_name = f"hullq_s0055niq_{uuid.uuid4().hex[:16]}"
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
def api_conn(api_url: str) -> Generator[Any]:
    conn = psycopg.connect(api_url)
    try:
        yield conn
    finally:
        conn.close()


def _as_of() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Domain/fixture helpers
# ---------------------------------------------------------------------------


def _insert_boat_design(
    conn: Any,
    design_id: str,
    model_id: str,
    *,
    baseline_keel_type: str,
    baseline_draft_max_m: float = 1.30,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps(
            {
                "dimensions": {"draft_max_m": baseline_draft_max_m},
                "appendages": {"keel_type": baseline_keel_type},
            }
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", baseline_json, "[]", "[]", "{}", "1" * 64],
        )
    conn.commit()


def _insert_boat_design_with_keel_variant(
    conn: Any,
    design_id: str,
    model_id: str,
    *,
    baseline_keel_type: str,
    variant_id: str,
    variant_keel_type: str,
    baseline_draft_max_m: float = 1.30,
) -> None:
    """Same as `_insert_boat_design` but with one NamedVariant carrying its
    own `appendages.keel_type` override -- used to prove
    `matching_configuration_ids` correctly identifies a NamedVariant
    configuration, not merely a BoatDesign id (Finding 1)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps(
            {
                "dimensions": {"draft_max_m": baseline_draft_max_m},
                "appendages": {"keel_type": baseline_keel_type},
            }
        )
        named_variants_json = json.dumps(
            [{"id": variant_id, "overrides": {"appendages": {"keel_type": variant_keel_type}}}]
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [
                design_id,
                model_id,
                "{}",
                "[]",
                baseline_json,
                named_variants_json,
                "[]",
                "{}",
                "1" * 64,
            ],
        )
    conn.commit()


def _admit_design_keel_and_draft(
    conn: Any,
    design_id: str,
    *,
    keel_type: str,
    draft_max_m: Decimal = Decimal("1.30"),
) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=draft_max_m,
        resolution_id=f"FR-DRAFT-{design_id}",
    )
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value=keel_type,
        resolution_id=f"FR-KEEL-{design_id}",
        fetch_canonical_value=lookup_keel_canonical_value,
    )


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


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    boat_design_id: str,
    reuse_physical_boat: bool = False,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    if not reuse_physical_boat:
        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(physical_boat_id), boat_design_ref=BoatDesignRef(boat_design_id)
            ),
        )
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
        ),
    )
    create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
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
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result
    return account, org, membership


def _write_claim(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    listing_id: str,
    revision_id: str,
    draft: DraftClaim | None = None,
    keel_configuration: KeelConfigurationClaim | None = None,
) -> None:
    result = write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(revision_id),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            draft=draft,
            keel_configuration=keel_configuration,
        ),
    )
    assert result.status.value in ("created", "revised"), result


def _keel_value(value: str) -> KeelConfigurationClaim:
    return KeelConfigurationClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration(value)
    )


_KEEL_UNKNOWN = KeelConfigurationClaim(assertion_kind=AssertionKind.UNKNOWN)
_DRAFT_UNKNOWN = DraftClaim(assertion_kind=AssertionKind.UNKNOWN)


def _draft_value(value: str) -> DraftClaim:
    return DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal(value))


# ---------------------------------------------------------------------------
# Acceptance criterion 1/2: keel-only match / non-match / insufficient
# ---------------------------------------------------------------------------


def test_keel_only_confirmed_match(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-NIQ-1", "BM-NIQ-1", baseline_keel_type="fin")
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-1", keel_type="fin")
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-1",
        physical_boat_id="PB-NIQ-1",
        market_episode_id="ME-NIQ-1",
        boat_design_id="BD-NIQ-1",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-1",
        revision_id="REV-NIQ-1",
        keel_configuration=_keel_value("FIN"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-NIQ-1"}
    assert outcome.confirmed_non_match_count == 0
    assert outcome.insufficient_data_count == 0

    match = outcome.confirmed_matches[0]
    # Finding 1: the resolved BoatDesign configuration identity that admitted
    # the match is preserved, not collapsed to a bare design id.
    assert match.design_evaluation.design_id == "BD-NIQ-1"
    assert match.design_evaluation.result_class is ResultClass.CONFIRMED_MATCH
    assert match.design_evaluation.matching_configuration_ids == ("BD-NIQ-1::baseline",)
    evidence = match.concrete_criterion_evidence[0]
    assert evidence.criterion.field == "keel_configuration"
    assert evidence.criterion.equals == "FIN"
    assert evidence.observed_value == "FIN"

    # Second amendment, Finding 1 (Required tests): the baseline design-side
    # match exposes its own typed observed canonical value ("FIN", mapped
    # from the BoatDesign keel_type "fin") and the baseline configuration
    # identity -- not only the aggregate matching_configuration_ids.
    assert len(match.design_configuration_evidence) == 1
    baseline_evidence = match.design_configuration_evidence[0]
    assert baseline_evidence.configuration_id == "BD-NIQ-1::baseline"
    assert baseline_evidence.boat_design_id == "BD-NIQ-1"
    assert baseline_evidence.named_variant_id is None
    assert baseline_evidence.truth.value == "TRUE"
    design_keel_evidence = baseline_evidence.criterion_evidence[0]
    assert design_keel_evidence.criterion.field == "keel_configuration"
    assert design_keel_evidence.observed_value == "FIN"


def test_keel_only_confirmed_non_match(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-NIQ-2", "BM-NIQ-2", baseline_keel_type="fin")
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-2", keel_type="fin")
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-2",
        physical_boat_id="PB-NIQ-2",
        market_episode_id="ME-NIQ-2",
        boat_design_id="BD-NIQ-2",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-2",
        revision_id="REV-NIQ-2",
        keel_configuration=_keel_value("WING"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert outcome.confirmed_non_match_count == 1
    assert outcome.confirmed_non_matches[0].native_listing_id.value == "NL-NIQ-2"


def test_keel_only_confirmed_match_preserves_named_variant_configuration_identity(
    api_conn: Any,
) -> None:
    """Finding 1 (Required tests): a NamedVariant match must preserve the
    correct NamedVariant configuration identity, not the baseline's -- the
    baseline here is a design-level non-match (`wing`) and only the
    NamedVariant override (`fin`) makes the design eligible."""
    _insert_boat_design_with_keel_variant(
        api_conn,
        "BD-NIQ-VAR",
        "BM-NIQ-VAR",
        baseline_keel_type="wing",
        variant_id="VAR-NIQ-1",
        variant_keel_type="fin",
    )
    admit_resolved_categorical_field(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id="BD-NIQ-VAR",
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value="wing",
        resolution_id="FR-KEEL-BD-NIQ-VAR",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    admit_resolved_categorical_field(
        api_conn,
        subject_kind=SubjectKind.NAMED_VARIANT,
        subject_id="VAR-NIQ-1",
        field_pointer=KEEL_TYPE_OVERRIDE_FIELD_POINTER,
        value="fin",
        resolution_id="FR-KEEL-VAR-NIQ-1",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-VAR",
        physical_boat_id="PB-NIQ-VAR",
        market_episode_id="ME-NIQ-VAR",
        boat_design_id="BD-NIQ-VAR",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-VAR",
        revision_id="REV-NIQ-VAR",
        keel_configuration=_keel_value("FIN"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-NIQ-VAR"}
    match = outcome.confirmed_matches[0]
    assert match.design_evaluation.matching_configuration_ids == ("BD-NIQ-VAR::VAR-NIQ-1",)
    assert outcome.insufficient_data_count == 0

    # Second amendment, Finding 1 (Required tests): the NamedVariant match
    # exposes its own typed observed value ("FIN") under the correct
    # NamedVariant configuration identity, distinct from the baseline's own
    # (non-matching, "WING") evidence -- both are retained, not only the
    # matching one.
    evidence_by_configuration_id = {
        e.configuration_id: e for e in match.design_configuration_evidence
    }
    assert set(evidence_by_configuration_id) == {"BD-NIQ-VAR::baseline", "BD-NIQ-VAR::VAR-NIQ-1"}
    variant_evidence = evidence_by_configuration_id["BD-NIQ-VAR::VAR-NIQ-1"]
    assert variant_evidence.named_variant_id == "VAR-NIQ-1"
    assert variant_evidence.truth.value == "TRUE"
    assert variant_evidence.criterion_evidence[0].observed_value == "FIN"
    baseline_evidence = evidence_by_configuration_id["BD-NIQ-VAR::baseline"]
    assert baseline_evidence.named_variant_id is None
    assert baseline_evidence.truth.value == "FALSE"
    assert baseline_evidence.criterion_evidence[0].observed_value == "WING"


def test_keel_only_omitted_claim_is_insufficient_data(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-NIQ-3", "BM-NIQ-3", baseline_keel_type="fin")
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-3", keel_type="fin")
    _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-3",
        physical_boat_id="PB-NIQ-3",
        market_episode_id="ME-NIQ-3",
        boat_design_id="BD-NIQ-3",
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert outcome.confirmed_non_match_count == 0
    assert outcome.insufficient_data_count == 1
    assert outcome.insufficient_data[0].native_listing_id.value == "NL-NIQ-3"


def test_keel_only_unknown_claim_is_insufficient_data(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-NIQ-4", "BM-NIQ-4", baseline_keel_type="fin")
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-4", keel_type="fin")
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-4",
        physical_boat_id="PB-NIQ-4",
        market_episode_id="ME-NIQ-4",
        boat_design_id="BD-NIQ-4",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-4",
        revision_id="REV-NIQ-4",
        keel_configuration=_KEEL_UNKNOWN,
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert outcome.insufficient_data_count == 1


# ---------------------------------------------------------------------------
# Acceptance criterion 3/4: mixed draft_max AND keel_configuration
# ---------------------------------------------------------------------------


def test_mixed_draft_and_keel_confirmed_joint_match(api_conn: Any) -> None:
    _insert_boat_design(
        api_conn, "BD-NIQ-5", "BM-NIQ-5", baseline_keel_type="fin", baseline_draft_max_m=1.30
    )
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-5", keel_type="fin", draft_max_m=Decimal("1.30"))
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-5",
        physical_boat_id="PB-NIQ-5",
        market_episode_id="ME-NIQ-5",
        boat_design_id="BD-NIQ-5",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-5",
        revision_id="REV-NIQ-5",
        draft=_draft_value("1.40"),
        keel_configuration=_keel_value("FIN"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=Decimal("1.6"), keel_configuration="FIN", as_of=_as_of()
    )
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-NIQ-5"}
    match = outcome.confirmed_matches[0]
    evidence_by_field = {e.evaluation.field: e for e in match.concrete_criterion_evidence}
    assert set(evidence_by_field) == {"draft_max_m", "keel_configuration"}

    # Finding 1: requested value/comparison and safely observed value are
    # both typed, not only embedded in explanation text.
    draft_evidence = evidence_by_field["draft_max_m"]
    assert draft_evidence.criterion.threshold_max == Decimal("1.6")
    assert draft_evidence.observed_value == Decimal("1.40")
    keel_evidence = evidence_by_field["keel_configuration"]
    assert keel_evidence.criterion.equals == "FIN"
    assert keel_evidence.observed_value == "FIN"
    assert match.design_evaluation.result_class is ResultClass.CONFIRMED_MATCH

    # Second amendment, Finding 1 (Required tests): both criteria's typed
    # design-side observed values are preserved on the same resolved
    # (baseline) configuration.
    assert len(match.design_configuration_evidence) == 1
    baseline_evidence = match.design_configuration_evidence[0]
    assert baseline_evidence.configuration_id == "BD-NIQ-5::baseline"
    design_evidence_by_field = {e.evaluation.field: e for e in baseline_evidence.criterion_evidence}
    assert design_evidence_by_field["draft_max_m"].observed_value == Decimal("1.30")
    assert design_evidence_by_field["keel_configuration"].observed_value == "FIN"


def test_draft_true_keel_false_is_non_match_not_match(api_conn: Any) -> None:
    _insert_boat_design(
        api_conn, "BD-NIQ-6", "BM-NIQ-6", baseline_keel_type="fin", baseline_draft_max_m=1.30
    )
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-6", keel_type="fin", draft_max_m=Decimal("1.30"))
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-6",
        physical_boat_id="PB-NIQ-6",
        market_episode_id="ME-NIQ-6",
        boat_design_id="BD-NIQ-6",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-6",
        revision_id="REV-NIQ-6",
        draft=_draft_value("1.40"),  # satisfies draft_max=1.6 -> TRUE
        keel_configuration=_keel_value("WING"),  # != FIN -> FALSE
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=Decimal("1.6"), keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert outcome.confirmed_non_match_count == 1
    non_match = outcome.confirmed_non_matches[0]
    assert non_match.result_class is ResultClass.CONFIRMED_NON_MATCH
    assert non_match.design_evaluation.result_class is ResultClass.CONFIRMED_MATCH
    evidence_by_field = {e.evaluation.field: e for e in non_match.concrete_criterion_evidence}
    assert evidence_by_field["draft_max_m"].evaluation.truth.value == "TRUE"
    assert evidence_by_field["draft_max_m"].observed_value == Decimal("1.40")
    keel_evidence = evidence_by_field["keel_configuration"]
    assert keel_evidence.evaluation.truth.value == "FALSE"
    # The publisher's own contradicting claim is a safely observed value --
    # a confirmed FALSE is not the same as an unresolved/missing value.
    assert keel_evidence.observed_value == "WING"


def test_draft_true_keel_unknown_is_insufficient_not_match(api_conn: Any) -> None:
    _insert_boat_design(
        api_conn, "BD-NIQ-7", "BM-NIQ-7", baseline_keel_type="fin", baseline_draft_max_m=1.30
    )
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-7", keel_type="fin", draft_max_m=Decimal("1.30"))
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-7",
        physical_boat_id="PB-NIQ-7",
        market_episode_id="ME-NIQ-7",
        boat_design_id="BD-NIQ-7",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-7",
        revision_id="REV-NIQ-7",
        draft=_draft_value("1.40"),  # TRUE
        keel_configuration=_KEEL_UNKNOWN,  # UNKNOWN
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=Decimal("1.6"), keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert outcome.confirmed_non_match_count == 0
    assert outcome.insufficient_data_count == 1
    insufficient = outcome.insufficient_data[0]
    assert insufficient.design_evaluation.result_class is ResultClass.CONFIRMED_MATCH
    evidence_by_field = {e.evaluation.field: e for e in insufficient.concrete_criterion_evidence}
    assert evidence_by_field["draft_max_m"].evaluation.truth.value == "TRUE"
    assert evidence_by_field["draft_max_m"].observed_value == Decimal("1.40")
    keel_evidence = evidence_by_field["keel_configuration"]
    assert keel_evidence.evaluation.truth.value == "UNKNOWN"
    # An explicit UNKNOWN claim must never invent an observed value.
    assert keel_evidence.observed_value is None


# ---------------------------------------------------------------------------
# Acceptance criterion 5: same-PhysicalBoat cross-Organization contradiction
# ---------------------------------------------------------------------------


def test_cross_organization_keel_contradiction_blocks_confirmed_match(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-NIQ-8", "BM-NIQ-8", baseline_keel_type="fin")
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-8", keel_type="fin")
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-8",
        physical_boat_id="PB-NIQ-8",
        market_episode_id="ME-NIQ-8",
        boat_design_id="BD-NIQ-8",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-8",
        revision_id="REV-NIQ-8",
        keel_configuration=_keel_value("FIN"),
    )
    other_account = AccountId("ACC-NIQ-8-OTHER")
    other_org = _org("ORG-NIQ-8-OTHER")
    other_membership = _membership(other_org, other_account, "OM-NIQ-8-OTHER")
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-NIQ-8-OTHER"), physical_boat_id=PhysicalBoatId("PB-NIQ-8")
        ),
    )
    create_native_listing(
        api_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        listing=NativeListing(
            id=NativeListingId("NL-NIQ-8-OTHER"),
            market_episode_id=MarketEpisodeId("ME-NIQ-8-OTHER"),
        ),
    )
    _write_claim(
        api_conn,
        account=other_account,
        org=other_org,
        membership=other_membership,
        listing_id="NL-NIQ-8-OTHER",
        revision_id="REV-NIQ-8-OTHER",
        keel_configuration=_keel_value("WING"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert outcome.insufficient_data_count == 1
    insufficient = outcome.insufficient_data[0]
    assert insufficient.native_listing_id.value == "NL-NIQ-8"
    assert insufficient.design_evaluation.result_class is ResultClass.CONFIRMED_MATCH
    keel_evidence = insufficient.concrete_criterion_evidence[0]
    assert keel_evidence.evaluation.truth.value == "UNKNOWN"
    # The contradiction guard fails closed to MISSING even though the
    # publisher's own claim was VALUE_ASSERTION -- never invent an observed
    # value from a claim overruled by cross-Organization disagreement.
    assert keel_evidence.observed_value is None


# ---------------------------------------------------------------------------
# Acceptance criterion 6: unsupported design taxonomy mapping fails closed
# ---------------------------------------------------------------------------


def test_unsupported_design_keel_mapping_fails_closed_but_preserves_design_evidence(
    api_conn: Any,
) -> None:
    """Finding 1 (amendment): an unsupported BoatDesign keel mapping still
    fails closed -- the listing never becomes a confirmed match -- but it
    must no longer disappear from every production application evidence
    surface. It is classified `INSUFFICIENT_DATA` (design/configuration
    eligibility never admitted it to the concrete funnel at all) and its
    `design_evaluation` is retained, never guessed into a match/non-match."""
    _insert_boat_design(api_conn, "BD-NIQ-9", "BM-NIQ-9", baseline_keel_type="full")
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-9", keel_type="full")
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-9",
        physical_boat_id="PB-NIQ-9",
        market_episode_id="ME-NIQ-9",
        boat_design_id="BD-NIQ-9",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-9",
        revision_id="REV-NIQ-9",
        keel_configuration=_keel_value("FIN"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert outcome.confirmed_non_match_count == 0
    assert outcome.insufficient_data_count == 1
    insufficient = outcome.insufficient_data[0]
    assert insufficient.native_listing_id.value == "NL-NIQ-9"
    # Design-side evidence is retained: no matching configuration (the only
    # configuration's mapped value is unsupported -> UNKNOWN, never a
    # guessed TRUE/FALSE), and the concrete PhysicalBoat claim (which *did*
    # say FIN) was never even consulted -- design/configuration eligibility
    # never admitted this design to the concrete funnel (Required Behavior §C).
    assert insufficient.design_evaluation.design_id == "BD-NIQ-9"
    assert insufficient.design_evaluation.result_class is ResultClass.INSUFFICIENT_DATA
    assert insufficient.design_evaluation.matching_configuration_ids == ()
    assert insufficient.concrete_criterion_evidence == ()

    # Second amendment, Finding 1 (Required tests): typed design-side
    # evidence is retained even though the taxonomy mapping is unsupported --
    # never a fabricated mapped value, just an honest UNKNOWN/None.
    assert len(insufficient.design_configuration_evidence) == 1
    baseline_evidence = insufficient.design_configuration_evidence[0]
    assert baseline_evidence.configuration_id == "BD-NIQ-9::baseline"
    assert baseline_evidence.truth.value == "UNKNOWN"
    design_keel_evidence = baseline_evidence.criterion_evidence[0]
    assert design_keel_evidence.evaluation.truth.value == "UNKNOWN"
    assert design_keel_evidence.observed_value is None


def test_missing_design_side_keel_resolution_is_insufficient_but_preserves_evidence(
    api_conn: Any,
) -> None:
    """Finding 1 (Required tests): missing/unresolved design-side keel truth
    (no FieldResolution ever admitted for `appendages.keel_type`, even though
    the canonical JSON itself already says `fin`) remains outside primary
    matches but is not silently erased from the application evidence."""
    _insert_boat_design(api_conn, "BD-NIQ-NORES", "BM-NIQ-NORES", baseline_keel_type="fin")
    # Deliberately admit no FieldResolution at all for this design's keel
    # field -- raw canonical JSON presence alone must never self-authorize
    # confirmed Search truth (SLICE-0051 Finding 3, reused for keel).
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-NORES",
        physical_boat_id="PB-NIQ-NORES",
        market_episode_id="ME-NIQ-NORES",
        boat_design_id="BD-NIQ-NORES",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-NORES",
        revision_id="REV-NIQ-NORES",
        keel_configuration=_keel_value("FIN"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert outcome.insufficient_data_count == 1
    insufficient = outcome.insufficient_data[0]
    assert insufficient.native_listing_id.value == "NL-NIQ-NORES"
    assert insufficient.design_evaluation.result_class is ResultClass.INSUFFICIENT_DATA
    assert insufficient.design_evaluation.matching_configuration_ids == ()
    assert insufficient.concrete_criterion_evidence == ()

    # Second amendment, Finding 1 (Required tests): missing FieldResolution
    # exposes typed UNKNOWN/MISSING design evidence with observed_value is
    # None -- never a value fabricated from the raw canonical JSON alone.
    assert len(insufficient.design_configuration_evidence) == 1
    baseline_evidence = insufficient.design_configuration_evidence[0]
    assert baseline_evidence.truth.value == "UNKNOWN"
    design_keel_evidence = baseline_evidence.criterion_evidence[0]
    assert design_keel_evidence.evaluation.truth.value == "UNKNOWN"
    assert design_keel_evidence.evaluation.reason is not None
    assert design_keel_evidence.evaluation.reason.value == "VALUE_MISSING"
    assert design_keel_evidence.observed_value is None


# ---------------------------------------------------------------------------
# Acceptance criterion 9: criterion-level evidence for all three classes
# ---------------------------------------------------------------------------


def test_criterion_level_evidence_retained_for_every_result_class(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-NIQ-10", "BM-NIQ-10", baseline_keel_type="fin")
    _admit_design_keel_and_draft(api_conn, "BD-NIQ-10", keel_type="fin")

    match_listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-10-MATCH",
        physical_boat_id="PB-NIQ-10-MATCH",
        market_episode_id="ME-NIQ-10-MATCH",
        boat_design_id="BD-NIQ-10",
    )
    _write_claim(
        api_conn,
        account=match_listing[0],
        org=match_listing[1],
        membership=match_listing[2],
        listing_id="NL-NIQ-10-MATCH",
        revision_id="REV-NIQ-10-MATCH",
        keel_configuration=_keel_value("FIN"),
    )

    non_match_listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-10-NONMATCH",
        physical_boat_id="PB-NIQ-10-NONMATCH",
        market_episode_id="ME-NIQ-10-NONMATCH",
        boat_design_id="BD-NIQ-10",
    )
    _write_claim(
        api_conn,
        account=non_match_listing[0],
        org=non_match_listing[1],
        membership=non_match_listing[2],
        listing_id="NL-NIQ-10-NONMATCH",
        revision_id="REV-NIQ-10-NONMATCH",
        keel_configuration=_keel_value("WING"),
    )

    insufficient_listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-10-INSUFF",
        physical_boat_id="PB-NIQ-10-INSUFF",
        market_episode_id="ME-NIQ-10-INSUFF",
        boat_design_id="BD-NIQ-10",
    )
    _write_claim(
        api_conn,
        account=insufficient_listing[0],
        org=insufficient_listing[1],
        membership=insufficient_listing[2],
        listing_id="NL-NIQ-10-INSUFF",
        revision_id="REV-NIQ-10-INSUFF",
        keel_configuration=_KEEL_UNKNOWN,
    )

    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )

    assert len(outcome.confirmed_matches) == 1
    assert len(outcome.confirmed_non_matches) == 1
    assert len(outcome.insufficient_data) == 1
    for group in (
        outcome.confirmed_matches,
        outcome.confirmed_non_matches,
        outcome.insufficient_data,
    ):
        evaluation = group[0]
        # Design/configuration evidence is retained for every result class,
        # including confirmed-non-match/insufficient (Finding 1) -- here all
        # three listings share the same design-level CONFIRMED_MATCH design,
        # so they diverge only at the concrete PhysicalBoat level.
        assert evaluation.design_evaluation.design_id == "BD-NIQ-10"
        assert evaluation.design_evaluation.result_class is ResultClass.CONFIRMED_MATCH
        assert len(evaluation.concrete_criterion_evidence) == 1
        evidence = evaluation.concrete_criterion_evidence[0]
        assert evidence.evaluation.field == "keel_configuration"
        assert evidence.evaluation.explanation
        assert evidence.criterion.equals == "FIN"
        # Second amendment, Finding 1 (Required tests): design-side evidence
        # is present and identical across all three listings (they share the
        # same design-level CONFIRMED_MATCH design), and stays completely
        # separate from -- unaffected by -- each listing's own diverging
        # concrete PhysicalBoat evidence.
        assert len(evaluation.design_configuration_evidence) == 1
        design_evidence = evaluation.design_configuration_evidence[0]
        assert design_evidence.configuration_id == "BD-NIQ-10::baseline"
        assert design_evidence.criterion_evidence[0].observed_value == "FIN"

    assert outcome.confirmed_matches[0].concrete_criterion_evidence[0].observed_value == "FIN"
    assert outcome.confirmed_non_matches[0].concrete_criterion_evidence[0].observed_value == "WING"
    # An UNKNOWN claim never invents an observed value.
    assert outcome.insufficient_data[0].concrete_criterion_evidence[0].observed_value is None


def test_pure_draft_max_request_still_uses_unmodified_0051_outcome_shape(api_conn: Any) -> None:
    """Finding 1 (Required tests): existing pure `draft_max` SLICE-0051
    public behavior remains unchanged by this module's evidence-preservation
    amendment -- `evaluate_draft_max_requirement` (untouched) still returns
    the original counts-only `DraftMaxSearchOutcome`, never the SLICE-0055
    `NativeInventorySearchOutcome` shape, for the exact same design/listing
    this module's own keel funnel would otherwise classify."""
    from hullq.application.inventory_search import (
        DraftMaxSearchOutcome,
        evaluate_draft_max_requirement,
    )

    _insert_boat_design(
        api_conn, "BD-NIQ-0051", "BM-NIQ-0051", baseline_keel_type="fin", baseline_draft_max_m=1.30
    )
    _admit_design_keel_and_draft(
        api_conn, "BD-NIQ-0051", keel_type="fin", draft_max_m=Decimal("1.30")
    )
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-NIQ-0051",
        physical_boat_id="PB-NIQ-0051",
        market_episode_id="ME-NIQ-0051",
        boat_design_id="BD-NIQ-0051",
    )
    _write_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-NIQ-0051",
        revision_id="REV-NIQ-0051",
        draft=_draft_value("1.40"),
        keel_configuration=_keel_value("FIN"),
    )
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"), as_of=_as_of())
    assert isinstance(outcome, DraftMaxSearchOutcome)
    assert not hasattr(outcome, "query")
    assert not hasattr(outcome, "design_evaluation")
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-NIQ-0051"}
    assert outcome.confirmed_matches[0].resolved_draft_m == Decimal("1.40")


# ---------------------------------------------------------------------------
# Non-regression: mixed funnel is never reached for a pure draft_max request
# ---------------------------------------------------------------------------


def test_requires_at_least_one_active_criterion(api_conn: Any) -> None:
    with pytest.raises(ValueError):
        evaluate_native_inventory_requirements(
            api_conn, draft_max=None, keel_configuration=None, as_of=_as_of()
        )
