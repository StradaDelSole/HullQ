"""SLICE-0091 owner-visible proof -- explicit Sail/Power/Motorsailer vessel
category foundation, real PostgreSQL 18.

Demonstrates, end to end, through the real accepted persistence/application
paths (never a second truth engine, never a hand-simulated resolution):

    1. design-only SAIL                     (DesignVesselCategoryAssertion)
    2. concrete-only POWER                  (VesselCategoryClaim via the
                                              existing claim-revision writer)
    3. design/concrete agreement            -> SAIL
    4. design/concrete disagreement         -> CONFLICT (never a best guess)
    5. cross-Organization disagreement      -> CONFLICT
    6. no evidence at all (legacy null)     -> UNKNOWN, never SAIL
    7. retraction (POWER -> UNKNOWN)        -> a new revision, not an overwrite
    8. the real nine-criterion Sail funnel (`hullq.application.
       native_inventory_query.evaluate_native_inventory_requirements`):
       a legacy null-category listing keeps matching unchanged, while an
       otherwise-matching explicit-POWER listing is excluded -- never a
       falsely confirmed Sail match.

Every resolved category and its reason is printed in plain text -- the
tester sees the real classification without reading raw SQL (SLICE-0091 §E).

Requires ``HULLQ_TEST_DATABASE_URL``. Does not require the Astro/FastAPI web
stack: this slice adds no public Search facet, API endpoint or SSR surface
(§A/explicit boundaries) -- only a non-public internal readback foundation.

Run: uv run python scripts/inspect_slice_0091_vessel_category.py
"""

from __future__ import annotations

import os
import sys
import uuid
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def _base_db_url() -> str:
    url = os.environ.get("HULLQ_TEST_DATABASE_URL", "").strip()
    if not url:
        print("HULLQ_TEST_DATABASE_URL is not set.", file=sys.stderr)
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


def _insert_boat_design(conn: Any, design_id: str, model_id: str, *, keel_type: str) -> None:
    import json

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, json.dumps({"appendages": {"keel_type": keel_type}}), "1" * 64],
        )
    conn.commit()


def main() -> int:
    sys.stdout.reconfigure(line_buffering=True)  # see every check as it happens, never buffered
    base_url = _base_db_url()
    schema_name = f"hullq_s0091insp_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)
    ok = True
    conn: Any = None
    try:
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
            KeelConfiguration,
            KeelConfigurationClaim,
            PhysicalBoatClaimRevisionId,
            PhysicalBoatClaimSnapshot,
            VesselCategory,
            VesselCategoryClaim,
        )
        from hullq.domain.provenance import ResolverKind, ResolverMetadata, SubjectKind
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
        from hullq.domain.vessel_category import (
            BoatDesignCategoryAssertionId,
            DesignVesselCategoryAssertion,
        )
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )
        from hullq.persistence.boat_design_category import (
            CATALOG_CATEGORY_ADMISSION_IDENTIFIER,
            write_boat_design_category_assertion,
        )
        from hullq.persistence.market_episode import create_market_episode
        from hullq.persistence.native_listing import create_native_listing
        from hullq.persistence.native_listing_offer import (
            NativeListingOfferRevisionId,
            write_native_listing_offer_revision,
        )
        from hullq.persistence.physical_boat import create_physical_boat
        from hullq.persistence.physical_boat_claims import (
            write_physical_boat_claim_revision,
        )

        sys.path.insert(0, str(REPO_ROOT / "tests" / "persistence"))
        from _field_resolution_support import (
            admit_resolved_categorical_field,  # type: ignore[import-not-found]
        )

        from hullq.search.keel_design_bridge import lookup_keel_canonical_value

        url = _with_search_path(base_url, schema_name)
        print("SLICE-0091 VESSEL CATEGORY FOUNDATION PROOF\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head (includes vessel_category_foundation) -> OK\n")

        VA = AssertionKind.VALUE_ASSERTION
        UNK = AssertionKind.UNKNOWN

        def _issuer() -> ResolverMetadata:
            return ResolverMetadata(
                kind=ResolverKind.DETERMINISTIC_TOOL,
                identifier=CATALOG_CATEGORY_ADMISSION_IDENTIFIER,
                version="1",
            )

        conn = psycopg.connect(url)

        # --- 1. design-only SAIL --------------------------------------------
        _insert_boat_design(conn, "BD-1", "BM-1", keel_type="fin")
        write_boat_design_category_assertion(
            conn,
            boat_design_id="BD-1",
            assertion_id=BoatDesignCategoryAssertionId("BDCAT-1"),
            expected_current_assertion_id=None,
            assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
            issuer=_issuer(),
        )
        conn.commit()

        from hullq.application.vessel_category_resolution import (
            resolve_physical_boat_vessel_category,
        )

        create_physical_boat(
            conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-1"), boat_design_ref=BoatDesignRef("BD-1"))
        )
        r1 = resolve_physical_boat_vessel_category(
            conn, physical_boat_id=PhysicalBoatId("PB-1"), boat_design_ref=BoatDesignRef("BD-1")
        )
        conn.commit()  # a read leaves the connection non-IDLE; next write needs IDLE
        check1 = r1.resolution.value == "SAIL" and r1.reason.value == "DESIGN_ONLY"
        ok &= check1
        print(f"1. design-only SAIL -> resolution={r1.resolution.value} reason={r1.reason.value} -> {'OK' if check1 else 'FAIL'}")

        # --- 2. concrete-only POWER ------------------------------------------
        _insert_boat_design(conn, "BD-2", "BM-2", keel_type="fin")
        create_physical_boat(
            conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-2"), boat_design_ref=BoatDesignRef("BD-2"))
        )
        create_market_episode(
            conn, market_episode=MarketEpisode(id=MarketEpisodeId("ME-2"), physical_boat_id=PhysicalBoatId("PB-2"))
        )
        account2 = AccountId("ACC-2")
        org2 = MarketplaceOrganization(
            id=MarketplaceOrganizationId("ORG-2"),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership2 = OrganizationMembership(
            id=OrganizationMembershipId("OM-2"),
            account_id=account2,
            organization_id=org2.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        create_native_listing(
            conn,
            account_id=account2,
            candidate_organization=org2,
            membership=membership2,
            listing=NativeListing(id=NativeListingId("NL-2"), market_episode_id=MarketEpisodeId("ME-2")),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account2,
            candidate_organization=org2,
            membership=membership2,
            native_listing_id=NativeListingId("NL-2"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-2-1"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Jeanneau",
                model_designation_claim="Merry Fisher",
                build_year=BuildYearClaim(assertion_kind=VA, value=2020),
                vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            ),
        )
        conn.commit()
        r2 = resolve_physical_boat_vessel_category(
            conn, physical_boat_id=PhysicalBoatId("PB-2"), boat_design_ref=BoatDesignRef("BD-2")
        )
        conn.commit()
        check2 = r2.resolution.value == "POWER" and r2.reason.value == "CONCRETE_ONLY"
        ok &= check2
        print(f"2. concrete-only POWER -> resolution={r2.resolution.value} reason={r2.reason.value} -> {'OK' if check2 else 'FAIL'}")

        # --- 3. agreement -----------------------------------------------------
        _insert_boat_design(conn, "BD-3", "BM-3", keel_type="fin")
        write_boat_design_category_assertion(
            conn,
            boat_design_id="BD-3",
            assertion_id=BoatDesignCategoryAssertionId("BDCAT-3"),
            expected_current_assertion_id=None,
            assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
            issuer=_issuer(),
        )
        conn.commit()
        create_physical_boat(
            conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-3"), boat_design_ref=BoatDesignRef("BD-3"))
        )
        create_market_episode(
            conn, market_episode=MarketEpisode(id=MarketEpisodeId("ME-3"), physical_boat_id=PhysicalBoatId("PB-3"))
        )
        account3 = AccountId("ACC-3")
        org3 = MarketplaceOrganization(
            id=MarketplaceOrganizationId("ORG-3"),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership3 = OrganizationMembership(
            id=OrganizationMembershipId("OM-3"),
            account_id=account3,
            organization_id=org3.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        create_native_listing(
            conn,
            account_id=account3,
            candidate_organization=org3,
            membership=membership3,
            listing=NativeListing(id=NativeListingId("NL-3"), market_episode_id=MarketEpisodeId("ME-3")),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account3,
            candidate_organization=org3,
            membership=membership3,
            native_listing_id=NativeListingId("NL-3"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-3-1"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Oceanis 40",
                build_year=BuildYearClaim(assertion_kind=VA, value=2019),
                vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
            ),
        )
        conn.commit()
        r3 = resolve_physical_boat_vessel_category(
            conn, physical_boat_id=PhysicalBoatId("PB-3"), boat_design_ref=BoatDesignRef("BD-3")
        )
        conn.commit()
        check3 = r3.resolution.value == "SAIL" and r3.reason.value == "SOURCES_AGREE"
        ok &= check3
        print(f"3. design+concrete agree SAIL -> resolution={r3.resolution.value} reason={r3.reason.value} -> {'OK' if check3 else 'FAIL'}")

        # --- 4. design-vs-concrete conflict ------------------------------------
        write_physical_boat_claim_revision(
            conn,
            account_id=account3,
            candidate_organization=org3,
            membership=membership3,
            native_listing_id=NativeListingId("NL-3"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-3-2"),
            expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-3-1"),
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Oceanis 40",
                build_year=BuildYearClaim(assertion_kind=VA, value=2019),
                vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            ),
        )
        conn.commit()
        r4 = resolve_physical_boat_vessel_category(
            conn, physical_boat_id=PhysicalBoatId("PB-3"), boat_design_ref=BoatDesignRef("BD-3")
        )
        conn.commit()
        check4 = r4.resolution.value == "CONFLICT" and r4.reason.value == "DESIGN_CONCRETE_DISAGREEMENT"
        ok &= check4
        print(f"4. design SAIL vs concrete POWER -> resolution={r4.resolution.value} reason={r4.reason.value} (never a guess) -> {'OK' if check4 else 'FAIL'}")

        # --- 5. cross-Organization disagreement --------------------------------
        account3b = AccountId("ACC-3B")
        org3b = MarketplaceOrganization(
            id=MarketplaceOrganizationId("ORG-3B"),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership3b = OrganizationMembership(
            id=OrganizationMembershipId("OM-3B"),
            account_id=account3b,
            organization_id=org3b.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        create_native_listing(
            conn,
            account_id=account3b,
            candidate_organization=org3b,
            membership=membership3b,
            listing=NativeListing(id=NativeListingId("NL-3B"), market_episode_id=MarketEpisodeId("ME-3")),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account3b,
            candidate_organization=org3b,
            membership=membership3b,
            native_listing_id=NativeListingId("NL-3B"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-3B-1"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Oceanis 40",
                build_year=BuildYearClaim(assertion_kind=VA, value=2019),
                vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
            ),
        )
        conn.commit()
        r5 = resolve_physical_boat_vessel_category(
            conn, physical_boat_id=PhysicalBoatId("PB-3"), boat_design_ref=BoatDesignRef("BD-3")
        )
        conn.commit()
        check5 = r5.resolution.value == "CONFLICT" and r5.reason.value == "CROSS_ORGANIZATION_DISAGREEMENT"
        ok &= check5
        print(f"5. two Organizations disagree (POWER vs SAIL) -> resolution={r5.resolution.value} reason={r5.reason.value} -> {'OK' if check5 else 'FAIL'}")

        # --- 6. no evidence at all (legacy null) -------------------------------
        _insert_boat_design(conn, "BD-6", "BM-6", keel_type="fin")
        create_physical_boat(
            conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-6"), boat_design_ref=BoatDesignRef("BD-6"))
        )
        r6 = resolve_physical_boat_vessel_category(
            conn, physical_boat_id=PhysicalBoatId("PB-6"), boat_design_ref=BoatDesignRef("BD-6")
        )
        conn.commit()
        check6 = r6.resolution.value == "UNKNOWN" and not r6.is_explicitly_non_sail_or_conflicted
        ok &= check6
        print(f"6. legacy null category (no evidence anywhere) -> resolution={r6.resolution.value} -> never excluded from Sail -> {'OK' if check6 else 'FAIL'}")

        # --- 7. retraction ------------------------------------------------------
        write_physical_boat_claim_revision(
            conn,
            account_id=account2,
            candidate_organization=org2,
            membership=membership2,
            native_listing_id=NativeListingId("NL-2"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-2-2"),
            expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-2-1"),
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Jeanneau",
                model_designation_claim="Merry Fisher",
                build_year=BuildYearClaim(assertion_kind=VA, value=2020),
                vessel_category=VesselCategoryClaim(assertion_kind=UNK, value=None),
            ),
        )
        conn.commit()
        r7 = resolve_physical_boat_vessel_category(
            conn, physical_boat_id=PhysicalBoatId("PB-2"), boat_design_ref=BoatDesignRef("BD-2")
        )
        conn.commit()
        check7 = r7.resolution.value == "UNKNOWN"
        ok &= check7
        print(f"7. retraction POWER -> UNKNOWN (new revision, not overwrite) -> resolution={r7.resolution.value} -> {'OK' if check7 else 'FAIL'}\n")

        # --- 7b. amendment Finding D: unauthorized issuer is rejected ----------
        from hullq.domain.provenance import ResolverKind as _RK

        _insert_boat_design(conn, "BD-7B", "BM-7B", keel_type="fin")
        untrusted_write = write_boat_design_category_assertion(
            conn,
            boat_design_id="BD-7B",
            assertion_id=BoatDesignCategoryAssertionId("BDCAT-7B-UNTRUSTED"),
            expected_current_assertion_id=None,
            assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.POWER),
            issuer=ResolverMetadata(kind=_RK.HUMAN, identifier="random-internal-caller", version=None),
        )
        check7b = untrusted_write.status.value == "issuer_not_authorized"
        ok &= check7b
        print(
            "7b. unauthorized HUMAN issuer attempting to install design category POWER -> "
            f"write status={untrusted_write.status.value} (no mutation) -> {'OK' if check7b else 'FAIL'}\n"
        )

        # --- 8. real nine-criterion Sail funnel exclusion ----------------------
        from datetime import UTC, datetime

        from hullq.application.native_inventory_query import evaluate_native_inventory_requirements
        from hullq.domain.media_gallery import MediaSourceKind
        from hullq.persistence.broker_identity import seed_marketplace_organization
        from hullq.persistence.media_gallery import (
            create_uploaded_image_placement,
            insert_approved_media_asset,
            set_cover,
        )
        from hullq.persistence.native_listing_lifecycle import publish_native_listing

        def _publish_matching_sail_listing(
            listing_id: str, physical_boat_id: str, market_episode_id: str, design_id: str,
            org_id: str, account_id: str, vessel_category: VesselCategoryClaim | None,
        ) -> None:
            _insert_boat_design(conn, design_id, f"BM-{design_id}", keel_type="fin")
            admit_resolved_categorical_field(
                conn,
                subject_kind=SubjectKind.BOAT_DESIGN,
                subject_id=design_id,
                field_pointer="/baseline/appendages/keel_type",
                value="fin",
                resolution_id=f"FR-KEEL-{design_id}",
                fetch_canonical_value=lookup_keel_canonical_value,
            )
            account = AccountId(account_id)
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId(org_id),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership = OrganizationMembership(
                id=OrganizationMembershipId(f"OM-{org_id}"),
                account_id=account,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id), boat_design_ref=BoatDesignRef(design_id))
            )
            create_market_episode(
                conn, market_episode=MarketEpisode(id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id))
            )
            create_native_listing(
                conn, account_id=account, candidate_organization=org, membership=membership,
                listing=NativeListing(id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)),
            )
            write_native_listing_offer_revision(
                conn, account_id=account, candidate_organization=org, membership=membership,
                native_listing_id=NativeListingId(listing_id),
                revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT, location_country="FR",
                    broker_description="A well-maintained boat.",
                    asking_price_amount=Decimal("150000.00"), currency="EUR",
                ),
            )
            write_physical_boat_claim_revision(
                conn, account_id=account, candidate_organization=org, membership=membership,
                native_listing_id=NativeListingId(listing_id),
                revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}-1"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau", model_designation_claim="Oceanis 40",
                    build_year=BuildYearClaim(assertion_kind=VA, value=2019),
                    keel_configuration=KeelConfigurationClaim(assertion_kind=VA, value=KeelConfiguration.FIN),
                    vessel_category=vessel_category,
                ),
            )
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account.value])
                seed_marketplace_organization(conn, org)
                asset = insert_approved_media_asset(
                    conn, owner_organization_id=org.id, uploaded_by_account_id=account,
                    rights_declared=True, source_kind=MediaSourceKind.BROKER_UPLOAD, source_reference=None,
                    original_object_key=f"original/{listing_id}", derivative_object_key=f"derivative/{listing_id}",
                    content_hash=f"hash-{listing_id}", mime_type="image/jpeg", width=800, height=600, byte_size=12345,
                )
                placement = create_uploaded_image_placement(
                    conn, native_listing_id=NativeListingId(listing_id), owner_organization_id=org.id, media_asset=asset
                )
                set_cover(
                    conn, native_listing_id=NativeListingId(listing_id), owner_organization_id=org.id,
                    media_placement_id=placement.media_placement_id, expected_version=placement.gallery_version,
                )
            publish_native_listing(
                conn, account_id=account, candidate_organization=org, membership=membership,
                native_listing_id=NativeListingId(listing_id),
            )

        _publish_matching_sail_listing("NL-LEG", "PB-LEG", "ME-LEG", "BD-LEG", "ORG-LEG", "ACC-LEG", None)
        _publish_matching_sail_listing(
            "NL-PWR", "PB-PWR", "ME-PWR", "BD-PWR", "ORG-PWR", "ACC-PWR",
            VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        )
        outcome = evaluate_native_inventory_requirements(
            conn, draft_max=None, keel_configuration="FIN", as_of=datetime.now(UTC)
        )
        matched_ids = {m.native_listing_id.value for m in outcome.confirmed_matches}
        check8 = "NL-LEG" in matched_ids and "NL-PWR" not in matched_ids
        ok &= check8
        print(
            "8. real nine-criterion Sail funnel: legacy listing NL-LEG still CONFIRMED_MATCH; "
            f"explicit-POWER listing NL-PWR excluded (never a falsely confirmed Sail match) -> "
            f"confirmed_matches={sorted(matched_ids)} -> {'OK' if check8 else 'FAIL'}\n"
        )

        conn.close()
        conn = None
        print(f"SLICE-0091 VESSEL CATEGORY FOUNDATION PROOF RESULT -> {'PASS' if ok else 'FAIL'} [SLICE-0091-DONE]")
        return 0 if ok else 1
    finally:
        # A connection left open (even idle-in-transaction holding only a
        # row-level AccessShareLock) blocks the DROP SCHEMA ... CASCADE
        # below forever -- always close it first, including on the
        # exception path, so a real bug fails fast with its traceback
        # instead of hanging on an unreleased lock.
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
