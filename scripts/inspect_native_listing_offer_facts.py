"""SLICE-0045 NativeListing offer-facts persistence owner-inspection.

Executes real PostgreSQL/Alembic behavior to demonstrate the durable
NativeListing offer capability required by SLICE-0045: authorized initial
AMOUNT offer creation with exact readback, idempotent same-revision retry,
a second revision that changes current state while the first revision
remains retained unchanged, a stale-expectation conflict that changes
nothing, cross-Organization denial that writes zero offer changes, a POA
revision with no invented price, explicit UNKNOWN /
NO_KNOWN_HISTORY_DECLARED examples surviving exact readback distinctly from
omission, and a VAT claim retained as an attributed, unverified broker
claim.

Run: uv run python scripts/inspect_native_listing_offer_facts.py

Requires HULLQ_TEST_DATABASE_URL to point at a local PostgreSQL 18 instance.
Runs against its own freshly created/dropped disposable PostgreSQL *schema*
(isolated via the connection ``options=-c search_path=...`` parameter), then
brings that schema from genuinely empty to the SLICE-0045 Alembic head
(SLICE-0043 baseline + native_listing_offer_facts revision).
"""

from __future__ import annotations

import sys
import uuid
from decimal import Decimal
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

from hullq.domain.market_identity import NativeListing, NativeListingId
from hullq.domain.native_listing_offer import (
    AskingPriceMode,
    AssertionKind,
    KnownHistoryNarrativeClaim,
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
    VatTaxStatusClaim,
    VatTaxStatusValue,
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
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferWriteStatus,
    fetch_current_native_listing_offer,
    fetch_native_listing_offer_revision,
    write_native_listing_offer_revision,
)

_LISTING_A_ID = "NL-0045-A"
_ORG_A_ID = "ORG-0045-A"
_ORG_B_ID = "ORG-0045-B"
_ACCOUNT_A_ID = "ACCOUNT-0045-A"
_ACCOUNT_B_ID = "ACCOUNT-0045-B"


def _base_url() -> str:
    import os

    url = os.environ.get(HULLQ_TEST_DATABASE_URL_ENV, "").strip()
    if not url:
        print(
            f"{HULLQ_TEST_DATABASE_URL_ENV} is not set. Point it at a disposable "
            "local PostgreSQL 18 instance, e.g.\n"
            f'  {HULLQ_TEST_DATABASE_URL_ENV}="postgresql://hullq_test:hullq_test@localhost:5432/hullq_test"',
            file=sys.stderr,
        )
        raise SystemExit(1)
    return url


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


def _amount_offer(**overrides: object) -> NativeListingOfferSnapshot:
    kwargs: dict[str, object] = {
        "asking_price_mode": AskingPriceMode.AMOUNT,
        "location_country": "FR",
        "broker_description": "A well-maintained cruising sloop, blue-water ready.",
        "asking_price_amount": Decimal("125000.00"),
        "currency": "EUR",
    }
    kwargs.update(overrides)
    return NativeListingOfferSnapshot(**kwargs)  # type: ignore[arg-type]


def main() -> int:
    base_url = _base_url()
    schema_name = f"hullq_s0045_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)
    url = _with_search_path(base_url, schema_name)

    try:
        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)

        conn = psycopg.connect(url)
        try:
            print("NATIVE LISTING OFFER FACTS\n")
            ok = True

            # -- setup: eligible Org A + a persisted SLICE-0043 NativeListing ---
            account_a = AccountId(_ACCOUNT_A_ID)
            org_a = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_A_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership_a = OrganizationMembership(
                id=OrganizationMembershipId("OM-0045-A"),
                account_id=account_a,
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            listing_create = create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                listing=NativeListing(id=NativeListingId(_LISTING_A_ID)),
            )
            conn.commit()
            print(f"NativeListing A setup      -> {listing_create.status.value.upper()}\n")

            # -- initial AMOUNT offer created + exact readback ------------------
            initial_offer = _amount_offer()
            create_result = write_native_listing_offer_revision(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId(_LISTING_A_ID),
                revision_id=NativeListingOfferRevisionId("REV-0045-A1"),
                expected_current_revision_id=None,
                offer=initial_offer,
            )
            conn.commit()
            record = fetch_current_native_listing_offer(conn, NativeListingId(_LISTING_A_ID))
            readback_exact = (
                record is not None
                and record.offer == initial_offer
                and record.publishing_organization_id == org_a.id
                and record.recorded_by_account_id == account_a
                and record.recorded_at is not None
            )
            created_ok = create_result.status is NativeListingOfferWriteStatus.CREATED
            ok &= created_ok and readback_exact
            print(f"initial AMOUNT offer       -> {create_result.status.value.upper()}")
            print(f"exact readback              -> {'EXACT' if readback_exact else 'MISMATCH'}\n")

            # -- same revision retry: idempotent ---------------------------------
            retry_result = write_native_listing_offer_revision(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId(_LISTING_A_ID),
                revision_id=NativeListingOfferRevisionId("REV-0045-A1"),
                expected_current_revision_id=None,
                offer=initial_offer,
            )
            conn.commit()
            retry_ok = retry_result.status is NativeListingOfferWriteStatus.ALREADY_EXISTS
            ok &= retry_ok
            print(f"same revision retry         -> {retry_result.status.value.upper()}\n")

            # -- second revision with expected current: current changes ---------
            second_offer = _amount_offer(asking_price_amount=Decimal("118000.00"))
            second_result = write_native_listing_offer_revision(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId(_LISTING_A_ID),
                revision_id=NativeListingOfferRevisionId("REV-0045-A2"),
                expected_current_revision_id=NativeListingOfferRevisionId("REV-0045-A1"),
                offer=second_offer,
            )
            conn.commit()
            current_after_second = fetch_current_native_listing_offer(
                conn, NativeListingId(_LISTING_A_ID)
            )
            first_revision_after_second = fetch_native_listing_offer_revision(
                conn, NativeListingOfferRevisionId("REV-0045-A1")
            )
            second_ok = (
                second_result.status is NativeListingOfferWriteStatus.REVISED
                and current_after_second is not None
                and current_after_second.revision_id == NativeListingOfferRevisionId("REV-0045-A2")
                and current_after_second.offer.asking_price_amount == Decimal("118000.00")
                and first_revision_after_second is not None
                and first_revision_after_second.offer.asking_price_amount == Decimal("125000.00")
            )
            ok &= second_ok
            print(f"second revision              -> {second_result.status.value.upper()}")
            print(
                "current asking price         -> "
                f"{current_after_second.offer.asking_price_amount if current_after_second else None}"
            )
            print(
                "first revision still exists  -> "
                f"{'YES' if first_revision_after_second is not None else 'NO'} "
                f"(amount={first_revision_after_second.offer.asking_price_amount if first_revision_after_second else None})\n"
            )

            # -- stale expected revision: CONFLICT, current unchanged -----------
            stale_result = write_native_listing_offer_revision(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId(_LISTING_A_ID),
                revision_id=NativeListingOfferRevisionId("REV-0045-A-STALE"),
                expected_current_revision_id=NativeListingOfferRevisionId("REV-0045-A1"),
                offer=_amount_offer(asking_price_amount=Decimal("1.00")),
            )
            conn.commit()
            current_after_stale = fetch_current_native_listing_offer(
                conn, NativeListingId(_LISTING_A_ID)
            )
            stale_ok = (
                stale_result.status is NativeListingOfferWriteStatus.CONFLICT
                and current_after_stale is not None
                and current_after_stale.revision_id == NativeListingOfferRevisionId("REV-0045-A2")
            )
            ok &= stale_ok
            print(f"stale expected revision      -> {stale_result.status.value.upper()}")
            print(
                "current state unchanged      -> "
                f"{'YES' if stale_ok else 'NO'} (current={current_after_stale.revision_id.value if current_after_stale else None})\n"
            )

            # -- eligible Org B attempting to edit listing A: DENIED -------------
            account_b = AccountId(_ACCOUNT_B_ID)
            org_b = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_B_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership_b = OrganizationMembership(
                id=OrganizationMembershipId("OM-0045-B"),
                account_id=account_b,
                organization_id=org_b.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            cross_org_result = write_native_listing_offer_revision(
                conn,
                account_id=account_b,
                candidate_organization=org_b,
                membership=membership_b,
                native_listing_id=NativeListingId(_LISTING_A_ID),
                revision_id=NativeListingOfferRevisionId("REV-0045-CROSSORG"),
                expected_current_revision_id=None,
                offer=_amount_offer(asking_price_amount=Decimal("1.00")),
            )
            conn.commit()
            current_after_cross_org = fetch_current_native_listing_offer(
                conn, NativeListingId(_LISTING_A_ID)
            )
            cross_org_ok = (
                cross_org_result.status is NativeListingOfferWriteStatus.CROSS_ORGANIZATION_DENIED
                and current_after_cross_org is not None
                and current_after_cross_org.revision_id
                == NativeListingOfferRevisionId("REV-0045-A2")
            )
            ok &= cross_org_ok
            print(f"cross-Organization write     -> {cross_org_result.status.value.upper()}")
            print(f"zero offer changes            -> {'YES' if cross_org_ok else 'NO'}\n")

            # -- POA revision: amount absent, no invented price -------------------
            poa_listing = NativeListing(id=NativeListingId("NL-0045-POA"))
            create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                listing=poa_listing,
            )
            conn.commit()
            poa_offer = _amount_offer(
                asking_price_mode=AskingPriceMode.POA, asking_price_amount=None, currency=None
            )
            poa_result = write_native_listing_offer_revision(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=poa_listing.id,
                revision_id=NativeListingOfferRevisionId("REV-0045-POA"),
                expected_current_revision_id=None,
                offer=poa_offer,
            )
            conn.commit()
            poa_record = fetch_current_native_listing_offer(conn, poa_listing.id)
            poa_ok = (
                poa_result.status is NativeListingOfferWriteStatus.CREATED
                and poa_record is not None
                and poa_record.offer.asking_price_mode is AskingPriceMode.POA
                and poa_record.offer.asking_price_amount is None
                and poa_record.offer.currency is None
            )
            ok &= poa_ok
            print(f"POA revision                 -> {poa_result.status.value.upper()}")
            print(f"amount absent, no invention  -> {'YES' if poa_ok else 'NO'}\n")

            # -- explicit UNKNOWN / NO_KNOWN_HISTORY_DECLARED survive exact ------
            explicit_listing = NativeListing(id=NativeListingId("NL-0045-EXPLICIT"))
            create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                listing=explicit_listing,
            )
            conn.commit()
            explicit_offer = _amount_offer(
                known_history_narrative=KnownHistoryNarrativeClaim(
                    assertion_kind=AssertionKind.NO_KNOWN_HISTORY_DECLARED
                ),
                vat_tax_status_claim=VatTaxStatusClaim(assertion_kind=AssertionKind.UNKNOWN),
            )
            write_native_listing_offer_revision(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=explicit_listing.id,
                revision_id=NativeListingOfferRevisionId("REV-0045-EXPLICIT"),
                expected_current_revision_id=None,
                offer=explicit_offer,
            )
            conn.commit()
            explicit_record = fetch_current_native_listing_offer(conn, explicit_listing.id)
            explicit_ok = (
                explicit_record is not None
                and explicit_record.offer.known_history_narrative is not None
                and explicit_record.offer.known_history_narrative.assertion_kind
                is AssertionKind.NO_KNOWN_HISTORY_DECLARED
                and explicit_record.offer.vat_tax_status_claim is not None
                and explicit_record.offer.vat_tax_status_claim.assertion_kind
                is AssertionKind.UNKNOWN
                and explicit_record.offer.location_region is None  # omitted, distinct from explicit
            )
            ok &= explicit_ok
            print(
                "known_history_narrative      -> NO_KNOWN_HISTORY_DECLARED (explicit, not omission)"
            )
            print("vat_tax_status_claim         -> UNKNOWN (explicit, not omission)")
            print(
                f"omitted field stays omitted  -> {'YES' if explicit_record and explicit_record.offer.location_region is None else 'NO'}"
            )
            print(f"explicit assertions exact    -> {'YES' if explicit_ok else 'NO'}\n")

            # -- VAT claim: attributed broker claim, not HullQ verification -----
            vat_listing = NativeListing(id=NativeListingId("NL-0045-VAT"))
            create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                listing=vat_listing,
            )
            conn.commit()
            vat_offer = _amount_offer(
                vat_tax_status_claim=VatTaxStatusClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=VatTaxStatusValue.VAT_PAID
                )
            )
            write_native_listing_offer_revision(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=vat_listing.id,
                revision_id=NativeListingOfferRevisionId("REV-0045-VAT"),
                expected_current_revision_id=None,
                offer=vat_offer,
            )
            conn.commit()
            vat_record = fetch_current_native_listing_offer(conn, vat_listing.id)
            vat_ok = (
                vat_record is not None
                and vat_record.offer.vat_tax_status_claim is not None
                and vat_record.offer.vat_tax_status_claim.value is VatTaxStatusValue.VAT_PAID
                and vat_record.publishing_organization_id == org_a.id
                and vat_record.recorded_by_account_id == account_a
                and vat_record.recorded_at is not None
            )
            ok &= vat_ok
            print(
                f"VAT claim stored              -> {vat_record.offer.vat_tax_status_claim.value.value if vat_ok else 'MISMATCH'}"
            )
            print(
                f"attributed to Organization    -> {vat_record.publishing_organization_id.value if vat_record else None}"
            )
            print(
                f"attributed to Account          -> {vat_record.recorded_by_account_id.value if vat_record else None}"
            )
            print(
                "HullQ verification implied    -> NO (this module has no verified=true concept)\n"
            )

            print(f"NATIVE LISTING OFFER FACTS RESULT -> {'PASS' if ok else 'FAIL'}")
            return 0 if ok else 1
        finally:
            conn.close()
    finally:
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
