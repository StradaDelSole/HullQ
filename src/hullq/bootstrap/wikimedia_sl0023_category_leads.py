"""Wikimedia category identity-lead discovery pilot — SLICE-0023.

Implements the pure, deterministic measurement logic described in
``docs/slices/SLICE-0023-wikimedia-category-identity-lead-discovery-pilot.md``.

This module performs no network acquisition (that lives in
``hullq.sources.wikimedia`` and, for the bounded Wikidata CC0 quality sample,
the already-accepted ``hullq.sources.wikidata.WikidataAdapter``) and no
database access. Given already-acquired category-membership pages and
page->QID mappings, it:

- hard-asserts the accepted immutable SLICE-0017/0018/0021 inputs (1,829
  retained direct-discovery QIDs, 1,770 accepted AUTO_ADMIT universe, 1,772
  retained historical crosswalk entries, the 57-QID SLICE-0021 alternative
  union) before any live acquisition;
- enforces the three fixed category hard caps and the combined pre-dedup cap;
- consolidates per-category membership into unique pages, tracking
  cross-category duplicate page IDs and duplicate QIDs explicitly;
- categorizes every unique page/QID against the accepted retained boundaries
  (``accepted_direct_qid_overlap`` / ``retained_alternative_qid_overlap`` /
  ``incremental_qid_lead`` / ``no_wikidata_qid``);
- runs the SLICE-0021 exact (``strip().casefold()``-only) title-signal probe
  against the accepted 1,770 canonical labels/aliases for every page outside
  ``accepted_direct_qid_overlap``;
- assigns each ``incremental_qid_lead`` QID to exactly one primary sampling
  stratum under the fixed ``Trimarans > Catamarans > Keelboats`` precedence;
- selects a deterministic, hard-capped (<=90/30/30, <=150 total) SHA256-ordered
  quality sample with no cross-stratum backfill;
- enforces the fixed Wikipedia/Wikidata request ceilings;
- applies the precommitted, mechanical source-level recommendation rule.

Explicitly does NOT:
- create, modify or delete any canonical HullQ row;
- mint a HullQ ID for any lead;
- modify the accepted SLICE-0017/0018/0021 retained artifacts;
- add Wikipedia/Wikimedia to production discovery;
- promote category membership to canonical evidence;
- parse Wikipedia article prose/infobox content;
- perform any normalization beyond surrounding-whitespace trim + casefold for
  the title-signal probe.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from hullq.bootstrap.wikidata_sl0021_alt_discovery import (
    ACCEPTED_AUTO_ADMIT_COUNT,
    RETAINED_DIRECT_DISCOVERY_COUNT,
    SL0017_MANIFEST_PATH,
    SL0018_MANIFEST_PATH,
    AcceptedUniverse,
    build_accepted_label_index,
    load_and_fingerprint_immutable_inputs,
    normalize_exact,
    qid_sort_key,
)

__all__ = [
    "ACCEPTED_ALTERNATIVE_UNION_COUNT",
    "ACCEPTED_HISTORICAL_CROSSWALK_COUNT",
    "ACCEPTED_SL0021_DISCOVERY_PROBE_GIT_BLOB_SHA1",
    "ACCEPTED_SL0021_SAMPLED_CANDIDATES_GIT_BLOB_SHA1",
    "CATAMARANS",
    "CATEGORY_ROUTES",
    "CATEGORY_ROUTES_BY_NAME",
    "COMBINED_MEMBERSHIP_CAP",
    "KEELBOATS",
    "LOW_YIELD_THRESHOLD",
    "NOISE_THRESHOLD_PCT",
    "ROUTE_CATAMARANS",
    "ROUTE_KEELBOATS",
    "ROUTE_TRIMARANS",
    "SAMPLE_CAP_BY_STRATUM",
    "SAMPLE_TOTAL_CAP",
    "STRATUM_PRECEDENCE",
    "TOTAL_REQUEST_CEILING",
    "TRIMARANS",
    "WIKIDATA_REQUEST_CEILING",
    "WIKIPEDIA_PAGEPROPS_BATCH_SIZE",
    "WIKIPEDIA_REQUEST_CEILING",
    "CategoryPage",
    "CategoryRoute",
    "ImmutableBoundaries",
    "ImmutableBoundaryIntegrityError",
    "OverlapCategory",
    "OverlapSets",
    "QualityTag",
    "Recommendation",
    "RequestCeilingExceededError",
    "SampleSelection",
    "TitleSignalCategory",
    "apply_qid_mapping",
    "assign_primary_stratum",
    "build_accepted_label_index",
    "build_category_membership_record",
    "build_discovery_manifest_document",
    "build_incremental_by_stratum",
    "build_quality_sample_document",
    "build_request_breakdown",
    "build_request_ceiling_summary",
    "build_unique_pages",
    "canonical_page_url",
    "categorize_overlap",
    "classify_title_signal",
    "compute_overlap_sets",
    "compute_qid_categories",
    "compute_qid_multiplicity",
    "compute_qid_sha256",
    "determine_recommendation",
    "git_blob_sha1",
    "load_and_verify_immutable_boundaries",
    "recompute_rights_access_ok",
    "reconstruct_unique_pages_from_manifest",
    "select_deterministic_sample",
    "verify_category_record_self_consistency",
    "verify_discovery_manifest_derived_sets_self_consistency",
    "verify_immutable_boundaries_reference_self_consistency",
    "verify_quality_sample_self_consistency",
    "verify_request_breakdown_self_consistency",
    "verify_sample_selection_self_consistency",
    "verify_title_signal_rows_self_consistency",
    "verify_unique_pages_reconstruction_self_consistency",
    "verify_wikidata_context_coverage_self_consistency",
]

# ---------------------------------------------------------------------------
# Fixed category routes and caps (docs/slices/SLICE-0023-*.md "Fixed live
# discovery surfaces" / "Hard caps")
# ---------------------------------------------------------------------------

KEELBOATS = "Keelboats"
CATAMARANS = "Catamarans"
TRIMARANS = "Trimarans"


@dataclass(frozen=True)
class CategoryRoute:
    """One fixed, precommitted SLICE-0023 English-Wikipedia category root."""

    name: str
    hard_cap: int


ROUTE_KEELBOATS = CategoryRoute(KEELBOATS, 2000)
ROUTE_CATAMARANS = CategoryRoute(CATAMARANS, 250)
ROUTE_TRIMARANS = CategoryRoute(TRIMARANS, 200)
CATEGORY_ROUTES: tuple[CategoryRoute, ...] = (ROUTE_KEELBOATS, ROUTE_CATAMARANS, ROUTE_TRIMARANS)
CATEGORY_ROUTES_BY_NAME: dict[str, CategoryRoute] = {r.name: r for r in CATEGORY_ROUTES}

COMBINED_MEMBERSHIP_CAP = 2450

# Sampling-only precedence for multi-category incremental QIDs (highest first).
STRATUM_PRECEDENCE: tuple[str, ...] = (TRIMARANS, CATAMARANS, KEELBOATS)
SAMPLE_CAP_BY_STRATUM: dict[str, int] = {TRIMARANS: 30, CATAMARANS: 30, KEELBOATS: 90}
SAMPLE_TOTAL_CAP = 150

WIKIPEDIA_REQUEST_CEILING = 75
WIKIDATA_REQUEST_CEILING = 10
TOTAL_REQUEST_CEILING = 85

# Must match hullq.sources.wikimedia's private _PAGEPROPS_BATCH_SIZE exactly
# (cross-checked by a dedicated unit test); duplicated here rather than
# imported to preserve the established decoupling between this pure module
# and the network-adapter module (see hullq.bootstrap.wikidata_sl0021_alt_discovery
# for the same convention).
WIKIPEDIA_PAGEPROPS_BATCH_SIZE = 50

LOW_YIELD_THRESHOLD = 100
NOISE_THRESHOLD_PCT = 50.0

# ---------------------------------------------------------------------------
# Accepted immutable comparison boundaries (docs/slices/SLICE-0023-*.md
# "Immutable comparison boundaries")
# ---------------------------------------------------------------------------

ACCEPTED_HISTORICAL_CROSSWALK_COUNT = 1772
ACCEPTED_ALTERNATIVE_UNION_COUNT = 57

ACCEPTED_SL0021_DISCOVERY_PROBE_GIT_BLOB_SHA1 = "16af426991214c445a3c152aacbe56b8088958d6"
ACCEPTED_SL0021_SAMPLED_CANDIDATES_GIT_BLOB_SHA1 = "5b56851f0c719b8dcf830fcd0416471c6c60596c"

ROOT = Path(__file__).resolve().parents[3]
SL0021_DIR = ROOT / "research" / "bootstrap" / "wikidata" / "sl0021-alt-discovery"
SL0021_DISCOVERY_PROBE_PATH = SL0021_DIR / "discovery_probe.json"
SL0021_SAMPLED_CANDIDATES_PATH = SL0021_DIR / "sampled_candidates.json"


class ImmutableBoundaryIntegrityError(RuntimeError):
    """Raised when a retained SLICE-0017/0018/0021 input artifact no longer
    reproduces its accepted historical fingerprint/count/blob hash.

    SLICE-0023 MUST fail closed (BLOCKED) rather than silently measure
    against a drifted immutable boundary.
    """


class RequestCeilingExceededError(RuntimeError):
    """Raised when a retained (or projected) request count would exceed the
    fixed SLICE-0023 per-host or combined request ceiling.
    """


class CategoryCapExceededError(RuntimeError):
    """Raised when a retained category-membership record's own member count
    exceeds that category's fixed hard cap.

    A live acquisition run must detect cap exceedance in real time (before
    this record is ever built) and stop the slice BLOCKED; this is a
    defense-in-depth invariant check on the retained record itself.
    """


def git_blob_sha1(data: bytes) -> str:
    """Deterministic ``git hash-object`` blob SHA1 of raw file bytes.

    Used only to compare a retained artifact against the accepted immutable
    blob-hash pins from the controlling slice document; not a security
    digest.
    """
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


@dataclass(frozen=True)
class ImmutableBoundaries:
    """The immutable accepted SLICE-0017/0018/0021 comparison boundaries,
    loaded and fingerprinted once before any live acquisition.
    """

    accepted_universe: AcceptedUniverse
    retained_historical_crosswalk_count: int
    alternative_union_qids: frozenset[str]
    sl0021_discovery_probe_blob_sha1: str
    sl0021_sampled_candidates_blob_sha1: str

    @property
    def accepted_direct_qids(self) -> frozenset[str]:
        return self.accepted_universe.retained_direct_discovery_qids


def load_and_verify_immutable_boundaries(
    *,
    sl0017_manifest_path: Path = SL0017_MANIFEST_PATH,
    sl0018_manifest_path: Path = SL0018_MANIFEST_PATH,
    discovery_probe_path: Path = SL0021_DISCOVERY_PROBE_PATH,
    sampled_candidates_path: Path = SL0021_SAMPLED_CANDIDATES_PATH,
) -> ImmutableBoundaries:
    """Load, fingerprint and hard-assert every accepted SLICE-0023 immutable
    comparison boundary before any live acquisition: the retained 1,829-QID
    direct-discovery universe and 1,770 accepted AUTO_ADMIT universe (reusing
    the accepted SLICE-0021 loader, which already fails closed on SL0017/0018
    raw-byte SHA256 drift), the 1,772-entry retained historical crosswalk
    count, and the accepted SLICE-0021 57-QID alternative union pinned by
    exact Git blob SHA1 of ``discovery_probe.json`` / ``sampled_candidates.json``.

    Fails closed via ``ImmutableBoundaryIntegrityError`` (or the underlying
    ``ImmutableInputIntegrityError`` from the reused SLICE-0021 loader) before
    any network use if any boundary has drifted. Never writes to any input
    file.
    """
    accepted_universe = load_and_fingerprint_immutable_inputs(
        sl0017_manifest_path, sl0018_manifest_path
    )

    sl0018_manifest = json.loads(sl0018_manifest_path.read_bytes().decode("utf-8"))
    retained_crosswalk = sl0018_manifest.get("retained_crosswalk")
    if not isinstance(retained_crosswalk, list):
        raise ImmutableBoundaryIntegrityError(
            f"Retained SLICE-0018 manifest at {sl0018_manifest_path} is missing a "
            "retained_crosswalk list"
        )
    crosswalk_count = len(retained_crosswalk)
    if crosswalk_count != ACCEPTED_HISTORICAL_CROSSWALK_COUNT:
        raise ImmutableBoundaryIntegrityError(
            "Retained historical QID->HullQ-ID crosswalk count does not equal the accepted "
            f"{ACCEPTED_HISTORICAL_CROSSWALK_COUNT}: got {crosswalk_count}"
        )

    discovery_probe_bytes = discovery_probe_path.read_bytes()
    discovery_probe_blob_sha1 = git_blob_sha1(discovery_probe_bytes)
    if discovery_probe_blob_sha1 != ACCEPTED_SL0021_DISCOVERY_PROBE_GIT_BLOB_SHA1:
        raise ImmutableBoundaryIntegrityError(
            f"Retained SLICE-0021 discovery_probe.json at {discovery_probe_path} failed Git blob "
            f"integrity check: sha1={discovery_probe_blob_sha1!r}, expected "
            f"{ACCEPTED_SL0021_DISCOVERY_PROBE_GIT_BLOB_SHA1!r}"
        )

    sampled_candidates_bytes = sampled_candidates_path.read_bytes()
    sampled_candidates_blob_sha1 = git_blob_sha1(sampled_candidates_bytes)
    if sampled_candidates_blob_sha1 != ACCEPTED_SL0021_SAMPLED_CANDIDATES_GIT_BLOB_SHA1:
        raise ImmutableBoundaryIntegrityError(
            f"Retained SLICE-0021 sampled_candidates.json at {sampled_candidates_path} failed "
            f"Git blob integrity check: sha1={sampled_candidates_blob_sha1!r}, expected "
            f"{ACCEPTED_SL0021_SAMPLED_CANDIDATES_GIT_BLOB_SHA1!r}"
        )

    discovery_probe = json.loads(discovery_probe_bytes.decode("utf-8"))
    total_union_qids = discovery_probe.get("cross_route_overlap", {}).get("total_union_qids")
    if not isinstance(total_union_qids, list):
        raise ImmutableBoundaryIntegrityError(
            "Retained SLICE-0021 discovery_probe.json is missing "
            "cross_route_overlap.total_union_qids"
        )
    alternative_union_qids = frozenset(total_union_qids)
    if len(alternative_union_qids) != ACCEPTED_ALTERNATIVE_UNION_COUNT:
        raise ImmutableBoundaryIntegrityError(
            "Accepted SLICE-0021 alternative-route union does not equal the accepted "
            f"{ACCEPTED_ALTERNATIVE_UNION_COUNT}: got {len(alternative_union_qids)}"
        )

    return ImmutableBoundaries(
        accepted_universe=accepted_universe,
        retained_historical_crosswalk_count=crosswalk_count,
        alternative_union_qids=alternative_union_qids,
        sl0021_discovery_probe_blob_sha1=discovery_probe_blob_sha1,
        sl0021_sampled_candidates_blob_sha1=sampled_candidates_blob_sha1,
    )


# Defensive re-assertion of the accepted constants reused from SLICE-0021, so
# a future accidental edit to the imported module's constants cannot silently
# change SLICE-0023's own accepted boundaries without this module failing to
# import.
assert RETAINED_DIRECT_DISCOVERY_COUNT == 1829
assert ACCEPTED_AUTO_ADMIT_COUNT == 1770


# ---------------------------------------------------------------------------
# Category-membership record construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CategoryPage:
    """One acquired main-namespace category-member page."""

    pageid: int
    title: str
    ns: int


def canonical_page_url(title: str) -> str:
    """Deterministic canonical English-Wikipedia page URL for a page title."""
    return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")


def build_category_membership_record(
    route: CategoryRoute,
    pages: Sequence[CategoryPage],
    *,
    acquired_at: str,
    request_count: int,
    continuation_count: int,
) -> dict[str, Any]:
    """Build one retained per-category membership record.

    ``pages`` MUST already be the complete, exhausted ``list=categorymembers``
    result for *route* (this function performs no network access itself).
    Fails closed on a duplicate page ID within one category's own membership
    stream (a correctly paginated ``cmnamespace=0`` result must never repeat a
    page) or on a member count exceeding the category's fixed hard cap — a
    live acquisition run MUST already have stopped BLOCKED before reaching
    this point in either case; this is defense-in-depth on the retained
    record itself.
    """
    page_list = list(pages)
    pageids = [p.pageid for p in page_list]
    if len(pageids) != len(set(pageids)):
        dupes = sorted({pid for pid in pageids if pageids.count(pid) > 1})
        raise ValueError(
            f"category {route.name!r}: duplicate page id(s) within one category's own "
            f"membership stream: {dupes}"
        )
    if len(page_list) > route.hard_cap:
        raise CategoryCapExceededError(
            f"category {route.name!r} returned {len(page_list)} main-namespace pages, "
            f"exceeding its hard cap of {route.hard_cap}"
        )
    return {
        "category": route.name,
        "hard_cap": route.hard_cap,
        "member_count": len(page_list),
        "cap_exceeded": False,
        "complete": True,
        "members": [
            {
                "pageid": p.pageid,
                "title": p.title,
                "ns": p.ns,
                "canonical_url": canonical_page_url(p.title),
            }
            for p in page_list
        ],
        "acquired_at": acquired_at,
        "request_count": request_count,
        "continuation_count": continuation_count,
    }


# ---------------------------------------------------------------------------
# Unique-page consolidation + duplicate tracking
# ---------------------------------------------------------------------------


def build_unique_pages(category_records: dict[str, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Consolidate per-category retained membership records into one
    ``page_id -> {title, canonical_url, categories}`` mapping.

    ``categories`` is the sorted tuple of every fixed category the page ID
    belongs to (cross-category duplicate page IDs have more than one entry).
    Fails closed if the same page ID reports an inconsistent title across
    categories (title/page-ID identity must be invariant).
    """
    pages: dict[int, dict[str, Any]] = {}
    for category_name, record in category_records.items():
        for m in record["members"]:
            pid = m["pageid"]
            if pid not in pages:
                pages[pid] = {
                    "pageid": pid,
                    "title": m["title"],
                    "canonical_url": m["canonical_url"],
                    "categories": {category_name},
                }
            else:
                if pages[pid]["title"] != m["title"]:
                    raise ValueError(
                        f"page id {pid} has inconsistent titles across categories: "
                        f"{pages[pid]['title']!r} vs {m['title']!r}"
                    )
                pages[pid]["categories"].add(category_name)
    return {
        pid: {**info, "categories": tuple(sorted(info["categories"]))}
        for pid, info in pages.items()
    }


def apply_qid_mapping(
    unique_pages: dict[int, dict[str, Any]], pageid_to_qid: dict[int, str]
) -> dict[int, dict[str, Any]]:
    """Merge a ``page_id -> QID`` mapping into consolidated unique pages.

    A page ID absent from *pageid_to_qid* is retained with ``qid: None``
    (``no_wikidata_qid``); this function never invents/infers a QID.
    """
    return {pid: {**info, "qid": pageid_to_qid.get(pid)} for pid, info in unique_pages.items()}


def compute_qid_multiplicity(
    pages_with_qid: dict[int, dict[str, Any]],
) -> dict[str, tuple[int, ...]]:
    """Group unique page IDs by their mapped QID, in ascending page-ID order.

    A QID with more than one owning page ID is a cross-surface "duplicate
    QID" and MUST be retained/measured explicitly (controlling slice
    "Page-to-Wikidata mapping and overlap categories").
    """
    result: dict[str, list[int]] = {}
    for pid, info in pages_with_qid.items():
        qid = info.get("qid")
        if qid is not None:
            result.setdefault(qid, []).append(pid)
    return {qid: tuple(sorted(pids)) for qid, pids in result.items()}


# ---------------------------------------------------------------------------
# Overlap categorization (accepted_direct / retained_alternative / incremental / no_qid)
# ---------------------------------------------------------------------------


class OverlapCategory(StrEnum):
    """The four deterministic per-QID/page overlap categories (controlling
    slice "Page-to-Wikidata mapping and overlap categories").
    """

    ACCEPTED_DIRECT_QID_OVERLAP = "accepted_direct_qid_overlap"
    RETAINED_ALTERNATIVE_QID_OVERLAP = "retained_alternative_qid_overlap"
    INCREMENTAL_QID_LEAD = "incremental_qid_lead"
    NO_WIKIDATA_QID = "no_wikidata_qid"


def categorize_overlap(
    qid: str | None,
    *,
    accepted_direct_qids: frozenset[str],
    alternative_union_qids: frozenset[str],
) -> OverlapCategory:
    """Deterministically categorize one QID (or absent QID) against the
    accepted retained boundaries. ``incremental_qid_lead`` means only that
    this bounded probe found the QID in neither accepted retained set — it
    does not prove global novelty or authorize admission.
    """
    if qid is None:
        return OverlapCategory.NO_WIKIDATA_QID
    if qid in accepted_direct_qids:
        return OverlapCategory.ACCEPTED_DIRECT_QID_OVERLAP
    if qid in alternative_union_qids:
        return OverlapCategory.RETAINED_ALTERNATIVE_QID_OVERLAP
    return OverlapCategory.INCREMENTAL_QID_LEAD


@dataclass(frozen=True)
class OverlapSets:
    """Deduplicated overlap-category sets: three are unique-QID sets, and
    ``no_wikidata_qid_pageids`` is a unique-page-ID set (pages without any
    linked QID have no QID to deduplicate by).
    """

    accepted_direct_qid_overlap: frozenset[str]
    retained_alternative_qid_overlap: frozenset[str]
    incremental_qid_lead: frozenset[str]
    no_wikidata_qid_pageids: frozenset[int]


def compute_overlap_sets(
    qid_multiplicity: dict[str, tuple[int, ...]],
    no_qid_pageids: frozenset[int],
    *,
    accepted_direct_qids: frozenset[str],
    alternative_union_qids: frozenset[str],
) -> OverlapSets:
    """Compute the four deduplicated overlap-category sets from the unique
    QID->page-ID grouping and the unique no-QID page-ID set.
    """
    accepted_direct: set[str] = set()
    retained_alt: set[str] = set()
    incremental: set[str] = set()
    for qid in qid_multiplicity:
        category = categorize_overlap(
            qid,
            accepted_direct_qids=accepted_direct_qids,
            alternative_union_qids=alternative_union_qids,
        )
        if category is OverlapCategory.ACCEPTED_DIRECT_QID_OVERLAP:
            accepted_direct.add(qid)
        elif category is OverlapCategory.RETAINED_ALTERNATIVE_QID_OVERLAP:
            retained_alt.add(qid)
        elif category is OverlapCategory.INCREMENTAL_QID_LEAD:
            incremental.add(qid)
    return OverlapSets(
        accepted_direct_qid_overlap=frozenset(accepted_direct),
        retained_alternative_qid_overlap=frozenset(retained_alt),
        incremental_qid_lead=frozenset(incremental),
        no_wikidata_qid_pageids=no_qid_pageids,
    )


# ---------------------------------------------------------------------------
# Multi-category primary-stratum assignment (Trimarans > Catamarans > Keelboats)
# ---------------------------------------------------------------------------


def compute_qid_categories(
    qid: str,
    qid_multiplicity: dict[str, tuple[int, ...]],
    unique_pages: dict[int, dict[str, Any]],
) -> frozenset[str]:
    """The set of fixed categories any page owning *qid* belongs to."""
    categories: set[str] = set()
    for pid in qid_multiplicity[qid]:
        categories.update(unique_pages[pid]["categories"])
    return frozenset(categories)


def assign_primary_stratum(category_memberships: frozenset[str]) -> str:
    """Assign the single highest-precedence sampling stratum for
    *category_memberships*, under the fixed, binding
    ``Trimarans > Catamarans > Keelboats`` precedence. All original category
    memberships remain retained separately in the discovery evidence; this
    assignment affects sampling only.
    """
    for stratum in STRATUM_PRECEDENCE:
        if stratum in category_memberships:
            return stratum
    raise ValueError(f"QID has no recognized fixed-category membership: {category_memberships!r}")


def build_incremental_by_stratum(
    incremental_qids: frozenset[str],
    qid_multiplicity: dict[str, tuple[int, ...]],
    unique_pages: dict[int, dict[str, Any]],
) -> dict[str, frozenset[str]]:
    """Partition every ``incremental_qid_lead`` QID into exactly one primary
    sampling stratum, keyed by ``STRATUM_PRECEDENCE`` order.
    """
    result: dict[str, set[str]] = {stratum: set() for stratum in STRATUM_PRECEDENCE}
    for qid in incremental_qids:
        categories = compute_qid_categories(qid, qid_multiplicity, unique_pages)
        stratum = assign_primary_stratum(categories)
        result[stratum].add(qid)
    return {stratum: frozenset(qids) for stratum, qids in result.items()}


# ---------------------------------------------------------------------------
# Deterministic SHA256 quality-sample selection
# ---------------------------------------------------------------------------


def compute_qid_sha256(qid: str) -> str:
    """Deterministic SHA256 digest of the UTF-8 QID string, the fixed
    sampling sort key (controlling slice "Deterministic Wikidata CC0 quality
    sample").
    """
    return hashlib.sha256(qid.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SampleSelection:
    """The deterministic, per-stratum-capped (<=90/30/30, no cross-stratum
    backfill) quality-sample selection.

    ``selected_by_stratum`` preserves the ascending-SHA256 selection order
    (the selection proof); ``selected_qids`` is the union in ascending
    numeric-QID order for stable retained-document readability.
    """

    selected_by_stratum: dict[str, tuple[str, ...]]
    selected_qids: tuple[str, ...]


def select_deterministic_sample(
    incremental_by_stratum: dict[str, frozenset[str]],
) -> SampleSelection:
    """Select the deterministic quality sample: within each stratum, sort its
    incremental QIDs by ascending SHA256 of the UTF-8 QID string and take the
    first N up to that stratum's fixed cap. Never backfills unused capacity
    from another stratum, so the total selected count may be below 150.
    """
    selected_by_stratum: dict[str, tuple[str, ...]] = {}
    pool: set[str] = set()
    for stratum in STRATUM_PRECEDENCE:
        cap = SAMPLE_CAP_BY_STRATUM[stratum]
        ordered = sorted(incremental_by_stratum.get(stratum, frozenset()), key=compute_qid_sha256)
        chosen = tuple(ordered[:cap])
        selected_by_stratum[stratum] = chosen
        pool.update(chosen)
    selected_qids = tuple(sorted(pool, key=qid_sort_key))
    return SampleSelection(selected_by_stratum=selected_by_stratum, selected_qids=selected_qids)


# ---------------------------------------------------------------------------
# Exact-only title-signal probe (reuses the SLICE-0021 trim+casefold rule)
# ---------------------------------------------------------------------------


class TitleSignalCategory(StrEnum):
    """The three exact title-signal categories (controlling slice "Exact
    identity-signal comparison"). Applied only to pages outside
    ``accepted_direct_qid_overlap``.
    """

    EXACT_SIGNAL_OTHER_QID = "exact_signal_other_qid"
    NO_EXACT_SIGNAL = "no_exact_signal"
    UNRESOLVED_STRUCTURAL = "unresolved_structural"


def classify_title_signal(
    title: str, *, accepted_label_index: dict[str, frozenset[str]]
) -> tuple[TitleSignalCategory, tuple[str, ...]]:
    """Classify one Wikipedia page title's exact identity signal against the
    accepted 1,770 canonical BoatModel labels/aliases, using ONLY the SLICE-0021
    ``value.strip().casefold()`` rule. No internal-whitespace collapse,
    punctuation rewriting, manufacturer-prefix manipulation, token
    reordering, fuzzy matching, or generation collapsing is ever applied.
    """
    key = normalize_exact(title)
    owners = accepted_label_index.get(key, frozenset())
    if not owners:
        return TitleSignalCategory.NO_EXACT_SIGNAL, ()
    if len(owners) > 1:
        return TitleSignalCategory.UNRESOLVED_STRUCTURAL, tuple(sorted(owners))
    return TitleSignalCategory.EXACT_SIGNAL_OTHER_QID, tuple(sorted(owners))


# ---------------------------------------------------------------------------
# Quality tag vocabulary + mechanical recommendation rule
# ---------------------------------------------------------------------------


class QualityTag(StrEnum):
    """The exactly-one-per-sample research-only quality tag vocabulary
    (controlling slice "Research-only quality review").
    """

    PLAUSIBLE_MODEL_OR_CLASS_LEAD = "plausible_model_or_class_lead"
    OBVIOUS_OUT_OF_SCOPE = "obvious_out_of_scope"
    AMBIGUOUS = "ambiguous"


class Recommendation(StrEnum):
    """The exactly-one source-level research recommendation vocabulary
    (controlling slice "Source-level recommendation"). Never authorizes
    production acquisition or canonical admission.
    """

    FOLLOWUP_VERIFICATION_CANDIDATE = "FOLLOWUP_VERIFICATION_CANDIDATE"
    LOW_INCREMENTAL_YIELD = "LOW_INCREMENTAL_YIELD"
    TOO_NOISY_FOR_FOLLOWUP = "TOO_NOISY_FOR_FOLLOWUP"
    RIGHTS_OR_ACCESS_BLOCKED = "RIGHTS_OR_ACCESS_BLOCKED"


def determine_recommendation(
    *,
    rights_access_ok: bool,
    unique_incremental_count: int,
    quality_tag_counts: dict[str, int],
) -> Recommendation:
    """Apply the precommitted, mechanical recommendation rule in order:

    1. rights/access violated or cannot be retained truthfully ->
       ``RIGHTS_OR_ACCESS_BLOCKED``;
    2. else unique ``incremental_qid_lead`` count below 100 ->
       ``LOW_INCREMENTAL_YIELD``;
    3. else fewer than 50% of the deterministic quality sample are
       ``plausible_model_or_class_lead`` -> ``TOO_NOISY_FOR_FOLLOWUP``
       (``ambiguous`` never counts as plausible; an empty sample is treated
       as 0% plausible, a fail-closed default);
    4. otherwise -> ``FOLLOWUP_VERIFICATION_CANDIDATE``.
    """
    if not rights_access_ok:
        return Recommendation.RIGHTS_OR_ACCESS_BLOCKED
    if unique_incremental_count < LOW_YIELD_THRESHOLD:
        return Recommendation.LOW_INCREMENTAL_YIELD
    total_sampled = sum(quality_tag_counts.values())
    plausible = quality_tag_counts.get(str(QualityTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD), 0)
    plausible_pct = (plausible / total_sampled * 100.0) if total_sampled else 0.0
    if plausible_pct < NOISE_THRESHOLD_PCT:
        return Recommendation.TOO_NOISY_FOR_FOLLOWUP
    return Recommendation.FOLLOWUP_VERIFICATION_CANDIDATE


# ---------------------------------------------------------------------------
# Request-ceiling enforcement (retained-document side; the live adapter
# enforces the same ceilings in real time before each dispatch)
# ---------------------------------------------------------------------------


def build_request_ceiling_summary(
    *, wikipedia_request_count: int, wikidata_request_count: int
) -> dict[str, Any]:
    """Build the retained request-ceiling summary, failing closed via
    ``RequestCeilingExceededError`` if any fixed ceiling was exceeded.
    """
    total = wikipedia_request_count + wikidata_request_count
    if wikipedia_request_count > WIKIPEDIA_REQUEST_CEILING:
        raise RequestCeilingExceededError(
            f"Wikipedia/MediaWiki request count {wikipedia_request_count} exceeds the fixed "
            f"ceiling of {WIKIPEDIA_REQUEST_CEILING}"
        )
    if wikidata_request_count > WIKIDATA_REQUEST_CEILING:
        raise RequestCeilingExceededError(
            f"Wikidata wbgetentities request count {wikidata_request_count} exceeds the fixed "
            f"ceiling of {WIKIDATA_REQUEST_CEILING}"
        )
    if total > TOTAL_REQUEST_CEILING:
        raise RequestCeilingExceededError(
            f"Total external HTTP request count {total} exceeds the fixed ceiling of "
            f"{TOTAL_REQUEST_CEILING}"
        )
    return {
        "wikipedia_request_count": wikipedia_request_count,
        "wikipedia_request_ceiling": WIKIPEDIA_REQUEST_CEILING,
        "wikidata_request_count": wikidata_request_count,
        "wikidata_request_ceiling": WIKIDATA_REQUEST_CEILING,
        "total_request_count": total,
        "total_request_ceiling": TOTAL_REQUEST_CEILING,
    }


def build_request_breakdown(
    *,
    category_records: dict[str, dict[str, Any]],
    pageprops_request_count: int,
    unique_page_count: int,
) -> dict[str, Any]:
    """Build the retained per-phase Wikipedia request breakdown, tying the
    aggregate ``wikipedia_request_count`` to independently-checkable
    structural facts rather than leaving it as an opaque total.

    ``pageprops_request_count`` MUST equal
    ``ceil(unique_page_count / WIKIPEDIA_PAGEPROPS_BATCH_SIZE)`` — the exact
    number of batched ``prop=pageprops`` requests the live run's own
    unique-page count implies — and the reconciled total (each fixed
    category's own retained ``request_count`` plus this pageprops-phase
    count) MUST equal the retained aggregate ``wikipedia_request_count``.
    Fails closed via ``ValueError`` if either check does not hold, so a
    fabricated or drifted breakdown can never be retained.
    """
    expected_pageprops = (
        -(-unique_page_count // WIKIPEDIA_PAGEPROPS_BATCH_SIZE) if unique_page_count else 0
    )
    if pageprops_request_count != expected_pageprops:
        raise ValueError(
            f"pageprops_request_count={pageprops_request_count} != expected "
            f"ceil({unique_page_count}/{WIKIPEDIA_PAGEPROPS_BATCH_SIZE})={expected_pageprops}"
        )
    category_requests = {
        name: category_records[name]["request_count"] for name in CATEGORY_ROUTES_BY_NAME
    }
    reconciled_total = sum(category_requests.values()) + pageprops_request_count
    return {
        "category_requests": category_requests,
        "pageprops_request_count": pageprops_request_count,
        "pageprops_batch_size": WIKIPEDIA_PAGEPROPS_BATCH_SIZE,
        "reconciled_wikipedia_request_count": reconciled_total,
    }


# ---------------------------------------------------------------------------
# Retained document assembly — JSON-primitive, pure (no network/DB access)
# ---------------------------------------------------------------------------

DISCOVERY_MANIFEST_SCHEMA_VERSION = "sl0023-discovery-manifest-v1"
QUALITY_SAMPLE_SCHEMA_VERSION = "sl0023-quality-sample-v1"


def build_discovery_manifest_document(
    *,
    generated_at: str,
    source_id: str,
    rights_gate: dict[str, str],
    boundaries: ImmutableBoundaries,
    category_records: dict[str, dict[str, Any]],
    unique_pages: dict[int, dict[str, Any]],
    qid_multiplicity: dict[str, tuple[int, ...]],
    no_qid_pageids: frozenset[int],
    overlap_sets: OverlapSets,
    title_signal_rows: list[dict[str, Any]],
    incremental_by_stratum: dict[str, frozenset[str]],
    sample: SampleSelection,
    request_ceiling_summary: dict[str, Any],
    pageprops_request_count: int,
) -> dict[str, Any]:
    """Assemble the retained ``discovery_manifest.json`` document."""
    if set(category_records) != {r.name for r in CATEGORY_ROUTES}:
        raise ValueError(
            f"category_records must be keyed by exactly {[r.name for r in CATEGORY_ROUTES]}; "
            f"got {sorted(category_records)}"
        )

    cross_category_duplicate_pageids = sorted(
        pid for pid, info in unique_pages.items() if len(info["categories"]) > 1
    )
    duplicate_qids = {qid: list(pids) for qid, pids in qid_multiplicity.items() if len(pids) > 1}

    title_signal_totals: dict[str, int] = {str(c): 0 for c in TitleSignalCategory}
    for row in title_signal_rows:
        title_signal_totals[row["title_signal_category"]] += 1

    request_breakdown = build_request_breakdown(
        category_records=category_records,
        pageprops_request_count=pageprops_request_count,
        unique_page_count=len(unique_pages),
    )
    if request_breakdown["reconciled_wikipedia_request_count"] != request_ceiling_summary.get(
        "wikipedia_request_count"
    ):
        raise ValueError(
            "request_breakdown.reconciled_wikipedia_request_count="
            f"{request_breakdown['reconciled_wikipedia_request_count']!r} != "
            f"request_ceiling_summary.wikipedia_request_count="
            f"{request_ceiling_summary.get('wikipedia_request_count')!r}"
        )

    return {
        "schema_version": DISCOVERY_MANIFEST_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_id": source_id,
        "rights_gate": dict(rights_gate),
        "immutable_boundaries": {
            "accepted_direct_discovery_count": len(boundaries.accepted_direct_qids),
            "accepted_auto_admit_count": len(
                boundaries.accepted_universe.accepted_auto_admit_identities
            ),
            "retained_historical_crosswalk_count": boundaries.retained_historical_crosswalk_count,
            "accepted_alternative_union_count": len(boundaries.alternative_union_qids),
            "sl0017_manifest_sha256": boundaries.accepted_universe.sl0017_sha256,
            "sl0018_manifest_sha256": boundaries.accepted_universe.sl0018_sha256,
            "sl0021_discovery_probe_git_blob_sha1": boundaries.sl0021_discovery_probe_blob_sha1,
            "sl0021_sampled_candidates_git_blob_sha1": boundaries.sl0021_sampled_candidates_blob_sha1,
        },
        "request_ceilings": request_ceiling_summary,
        "request_breakdown": request_breakdown,
        "categories": {name: category_records[name] for name in CATEGORY_ROUTES_BY_NAME},
        "cross_category_duplicate_pageids": cross_category_duplicate_pageids,
        "unique_page_count": len(unique_pages),
        "unique_pages": {
            str(pid): {
                "title": info["title"],
                "canonical_url": info["canonical_url"],
                "categories": list(info["categories"]),
                "qid": info.get("qid"),
            }
            for pid, info in sorted(unique_pages.items())
        },
        "page_qid_mapping": {
            "pages_with_qid_count": sum(len(pids) for pids in qid_multiplicity.values()),
            "unique_qid_count": len(qid_multiplicity),
            "no_qid_pageid_count": len(no_qid_pageids),
            "duplicate_qids": dict(sorted(duplicate_qids.items())),
        },
        "overlap_sets": {
            "accepted_direct_qid_overlap": {
                "count": len(overlap_sets.accepted_direct_qid_overlap),
                "qids": sorted(overlap_sets.accepted_direct_qid_overlap, key=qid_sort_key),
            },
            "retained_alternative_qid_overlap": {
                "count": len(overlap_sets.retained_alternative_qid_overlap),
                "qids": sorted(overlap_sets.retained_alternative_qid_overlap, key=qid_sort_key),
            },
            "incremental_qid_lead": {
                "count": len(overlap_sets.incremental_qid_lead),
                "qids": sorted(overlap_sets.incremental_qid_lead, key=qid_sort_key),
            },
            "no_wikidata_qid": {
                "count": len(overlap_sets.no_wikidata_qid_pageids),
                "pageids": sorted(overlap_sets.no_wikidata_qid_pageids),
            },
        },
        "title_signal": {
            "totals": title_signal_totals,
            "rows": title_signal_rows,
        },
        "primary_stratum_assignment": {
            stratum: {
                "count": len(qids),
                "qids": sorted(qids, key=qid_sort_key),
            }
            for stratum, qids in incremental_by_stratum.items()
        },
        "sample_selection": {
            "cap_by_stratum": dict(SAMPLE_CAP_BY_STRATUM),
            "total_cap": SAMPLE_TOTAL_CAP,
            "selected_by_stratum_sha256_order": {
                stratum: list(qids) for stratum, qids in sample.selected_by_stratum.items()
            },
            "selected_qids": list(sample.selected_qids),
            "selected_count": len(sample.selected_qids),
        },
    }


def build_quality_sample_document(
    *,
    generated_at: str,
    boundaries: ImmutableBoundaries,
    sample: SampleSelection,
    wikidata_context_rows: list[dict[str, Any]],
    quality_rows: list[dict[str, Any]],
    rights_access_ok: bool,
    unique_incremental_count: int,
) -> dict[str, Any]:
    """Assemble the retained ``quality_sample.json`` document.

    ``wikidata_context_rows`` are already-built minimal Wikidata CC0 context
    rows (QID, English label, English description, P31, P176/P287 if
    present). ``quality_rows`` are the manual per-QID
    ``{qid, quality_tag, rationale}`` review rows; this function validates
    the vocabulary/non-empty-rationale/exact-set-coverage invariants and
    computes totals/percentages/recommendation mechanically.

    ``unique_incremental_count`` MUST be the full (uncapped)
    ``overlap_sets.incremental_qid_lead`` count from the discovery manifest —
    the recommendation rule's <100 threshold applies to the true discovery
    yield, not merely the size of this (possibly smaller, <=150-capped)
    quality sample.
    """
    selected_set = frozenset(sample.selected_qids)
    quality_qids = frozenset(row["qid"] for row in quality_rows)
    if quality_qids != selected_set:
        missing = selected_set - quality_qids
        extra = quality_qids - selected_set
        raise ValueError(
            "quality_rows does not exactly cover the selected sample: "
            f"missing={sorted(missing, key=qid_sort_key)} extra={sorted(extra, key=qid_sort_key)}"
        )

    context_qid_list = [row["qid"] for row in wikidata_context_rows]
    context_qid_set = frozenset(context_qid_list)
    if len(context_qid_list) != len(context_qid_set):
        duplicates = sorted(
            {q for q in context_qid_list if context_qid_list.count(q) > 1}, key=qid_sort_key
        )
        raise ValueError(f"wikidata_context_rows contains duplicate QID(s): {duplicates}")
    if context_qid_set != selected_set:
        missing = selected_set - context_qid_set
        extra = context_qid_set - selected_set
        raise ValueError(
            "wikidata_context_rows does not exactly cover the selected sample: "
            f"missing={sorted(missing, key=qid_sort_key)} extra={sorted(extra, key=qid_sort_key)}"
        )

    valid_tags = {str(t) for t in QualityTag}
    for row in quality_rows:
        if row["quality_tag"] not in valid_tags:
            raise ValueError(f"candidate {row['qid']}: invalid quality_tag {row['quality_tag']!r}")
        if not row.get("rationale", "").strip():
            raise ValueError(f"candidate {row['qid']}: rationale must be a non-empty string")

    quality_tag_counts: dict[str, int] = {str(t): 0 for t in QualityTag}
    for row in quality_rows:
        quality_tag_counts[row["quality_tag"]] += 1
    total_sampled = len(quality_rows)
    quality_tag_percentages = {
        tag: round((count / total_sampled * 100.0) if total_sampled else 0.0, 4)
        for tag, count in quality_tag_counts.items()
    }

    return {
        "schema_version": QUALITY_SAMPLE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "accepted_universe_reference": {
            "sl0017_sha256": boundaries.accepted_universe.sl0017_sha256,
            "sl0018_sha256": boundaries.accepted_universe.sl0018_sha256,
            "accepted_auto_admit_count": len(
                boundaries.accepted_universe.accepted_auto_admit_identities
            ),
        },
        "selection_reference": {
            "selected_qids": list(sample.selected_qids),
            "selected_count": len(sample.selected_qids),
        },
        "wikidata_context": wikidata_context_rows,
        "quality_review": quality_rows,
        "quality_tag_counts": quality_tag_counts,
        "quality_tag_percentages": quality_tag_percentages,
        "total_sampled": total_sampled,
        "rights_access_ok": rights_access_ok,
        # Placeholder for the caller-supplied full incremental count; the
        # runner overwrites this with the true discovery-manifest value
        # before writing the retained document (see runner `_finalize_quality_sample`).
        "unique_incremental_qid_lead_count": unique_incremental_count,
        "recommendation": str(
            determine_recommendation(
                rights_access_ok=rights_access_ok,
                unique_incremental_count=unique_incremental_count,
                quality_tag_counts=quality_tag_counts,
            )
        ),
    }


# ---------------------------------------------------------------------------
# Offline self-consistency verification of already-retained documents
# ---------------------------------------------------------------------------


def verify_immutable_boundaries_reference_self_consistency(
    discovery_manifest: dict[str, Any], boundaries: ImmutableBoundaries
) -> list[str]:
    """Compare a retained ``discovery_manifest.json`` document's
    ``immutable_boundaries`` block against a freshly (re-)loaded
    ``ImmutableBoundaries`` (which itself already fails closed on drift).
    """
    mismatches: list[str] = []
    stored = discovery_manifest.get("immutable_boundaries", {})
    checks = {
        "accepted_direct_discovery_count": len(boundaries.accepted_direct_qids),
        "accepted_auto_admit_count": len(
            boundaries.accepted_universe.accepted_auto_admit_identities
        ),
        "retained_historical_crosswalk_count": boundaries.retained_historical_crosswalk_count,
        "accepted_alternative_union_count": len(boundaries.alternative_union_qids),
        "sl0017_manifest_sha256": boundaries.accepted_universe.sl0017_sha256,
        "sl0018_manifest_sha256": boundaries.accepted_universe.sl0018_sha256,
        "sl0021_discovery_probe_git_blob_sha1": boundaries.sl0021_discovery_probe_blob_sha1,
        "sl0021_sampled_candidates_git_blob_sha1": boundaries.sl0021_sampled_candidates_blob_sha1,
    }
    for key, expected in checks.items():
        if stored.get(key) != expected:
            mismatches.append(
                f"immutable_boundaries.{key}={stored.get(key)!r} != actual loaded {expected!r}"
            )
    if len(boundaries.accepted_direct_qids) != RETAINED_DIRECT_DISCOVERY_COUNT:
        mismatches.append(
            f"actual loaded accepted_direct_discovery_count={len(boundaries.accepted_direct_qids)!r}"
            f" != accepted constant {RETAINED_DIRECT_DISCOVERY_COUNT!r}"
        )
    if (
        len(boundaries.accepted_universe.accepted_auto_admit_identities)
        != ACCEPTED_AUTO_ADMIT_COUNT
    ):
        mismatches.append(
            "actual loaded accepted_auto_admit_count="
            f"{len(boundaries.accepted_universe.accepted_auto_admit_identities)!r} != accepted "
            f"constant {ACCEPTED_AUTO_ADMIT_COUNT!r}"
        )
    if boundaries.retained_historical_crosswalk_count != ACCEPTED_HISTORICAL_CROSSWALK_COUNT:
        mismatches.append(
            "actual loaded retained_historical_crosswalk_count="
            f"{boundaries.retained_historical_crosswalk_count!r} != accepted constant "
            f"{ACCEPTED_HISTORICAL_CROSSWALK_COUNT!r}"
        )
    if len(boundaries.alternative_union_qids) != ACCEPTED_ALTERNATIVE_UNION_COUNT:
        mismatches.append(
            f"actual loaded alternative_union_count={len(boundaries.alternative_union_qids)!r} "
            f"!= accepted constant {ACCEPTED_ALTERNATIVE_UNION_COUNT!r}"
        )
    return mismatches


def verify_category_record_self_consistency(name: str, record: dict[str, Any]) -> list[str]:
    """Recompute one retained category-membership record's
    ``member_count``/``hard_cap``/``cap_exceeded`` from its own retained
    ``members`` list and the fixed category-route definition.
    """
    route = CATEGORY_ROUTES_BY_NAME.get(name)
    if route is None:
        return [f"unknown category {name!r}"]
    mismatches: list[str] = []
    members = record.get("members", [])
    pageids = [m["pageid"] for m in members]
    if len(pageids) != len(set(pageids)):
        mismatches.append(f"{name}.members contains duplicate page id(s)")
    if record.get("member_count") != len(members):
        mismatches.append(
            f"{name}.member_count={record.get('member_count')!r} != len(members)={len(members)}"
        )
    if record.get("hard_cap") != route.hard_cap:
        mismatches.append(f"{name}.hard_cap={record.get('hard_cap')!r} != {route.hard_cap}")
    if len(members) > route.hard_cap:
        mismatches.append(f"{name}.member_count={len(members)} exceeds hard_cap={route.hard_cap}")
    for m in members:
        expected_url = canonical_page_url(m["title"])
        if m.get("canonical_url") != expected_url:
            mismatches.append(
                f"{name}: page {m.get('pageid')}.canonical_url={m.get('canonical_url')!r} != "
                f"recomputed {expected_url!r}"
            )
    return mismatches


def verify_request_breakdown_self_consistency(discovery_manifest: dict[str, Any]) -> list[str]:
    """Structurally verify the retained request-count summary, not merely
    that each count is individually below its ceiling.

    Recomputes, purely from the document's own retained facts (never from
    its own already-computed summary fields):

    - ``request_breakdown.category_requests`` from each fixed category's own
      retained ``request_count``;
    - ``request_breakdown.pageprops_request_count`` must equal
      ``ceil(unique_page_count / WIKIPEDIA_PAGEPROPS_BATCH_SIZE)``;
    - ``request_breakdown.reconciled_wikipedia_request_count`` (category
      requests + pageprops requests) must equal
      ``request_ceilings.wikipedia_request_count``;
    - ``request_ceilings.total_request_count`` must equal
      ``wikipedia_request_count + wikidata_request_count``;
    - every fixed ceiling must equal its accepted constant (75/10/85).

    This closes the gap where a tampered ``wikipedia_request_count`` could
    previously pass merely by staying under its ceiling, with no link back
    to the independently retained per-category/pageprops-phase facts.
    """
    mismatches: list[str] = []
    categories = discovery_manifest.get("categories", {})
    unique_page_count = discovery_manifest.get("unique_page_count", 0)
    stored_breakdown = discovery_manifest.get("request_breakdown", {})
    stored_ceilings = discovery_manifest.get("request_ceilings", {})

    expected_category_requests = {
        name: categories.get(name, {}).get("request_count") for name in CATEGORY_ROUTES_BY_NAME
    }
    if stored_breakdown.get("category_requests") != expected_category_requests:
        mismatches.append(
            "request_breakdown.category_requests does not match the retained "
            "categories.*.request_count values"
        )

    expected_pageprops = (
        -(-unique_page_count // WIKIPEDIA_PAGEPROPS_BATCH_SIZE) if unique_page_count else 0
    )
    stored_pageprops = stored_breakdown.get("pageprops_request_count")
    if stored_pageprops != expected_pageprops:
        mismatches.append(
            f"request_breakdown.pageprops_request_count={stored_pageprops!r} != recomputed "
            f"ceil({unique_page_count}/{WIKIPEDIA_PAGEPROPS_BATCH_SIZE})={expected_pageprops!r}"
        )
    if stored_breakdown.get("pageprops_batch_size") != WIKIPEDIA_PAGEPROPS_BATCH_SIZE:
        mismatches.append(
            f"request_breakdown.pageprops_batch_size={stored_breakdown.get('pageprops_batch_size')!r} "
            f"!= {WIKIPEDIA_PAGEPROPS_BATCH_SIZE!r}"
        )

    category_sum = sum(v for v in expected_category_requests.values() if isinstance(v, int))
    reconciled_total = category_sum + (stored_pageprops if isinstance(stored_pageprops, int) else 0)
    if stored_breakdown.get("reconciled_wikipedia_request_count") != reconciled_total:
        mismatches.append(
            "request_breakdown.reconciled_wikipedia_request_count="
            f"{stored_breakdown.get('reconciled_wikipedia_request_count')!r} != recomputed "
            f"{reconciled_total!r}"
        )
    if stored_ceilings.get("wikipedia_request_count") != reconciled_total:
        mismatches.append(
            "request_ceilings.wikipedia_request_count="
            f"{stored_ceilings.get('wikipedia_request_count')!r} != reconciled breakdown total "
            f"{reconciled_total!r}"
        )

    wp = stored_ceilings.get("wikipedia_request_count")
    wd = stored_ceilings.get("wikidata_request_count")
    if isinstance(wp, int) and isinstance(wd, int):
        expected_total = wp + wd
        if stored_ceilings.get("total_request_count") != expected_total:
            mismatches.append(
                f"request_ceilings.total_request_count={stored_ceilings.get('total_request_count')!r} "
                f"!= wikipedia_request_count + wikidata_request_count = {expected_total!r}"
            )
    fixed_ceilings = {
        "wikipedia_request_ceiling": WIKIPEDIA_REQUEST_CEILING,
        "wikidata_request_ceiling": WIKIDATA_REQUEST_CEILING,
        "total_request_ceiling": TOTAL_REQUEST_CEILING,
    }
    for key, expected in fixed_ceilings.items():
        if stored_ceilings.get(key) != expected:
            mismatches.append(
                f"request_ceilings.{key}={stored_ceilings.get(key)!r} != {expected!r}"
            )

    return mismatches


def verify_discovery_manifest_derived_sets_self_consistency(
    discovery_manifest: dict[str, Any],
    *,
    overlap_sets: OverlapSets,
    incremental_by_stratum: dict[str, frozenset[str]],
    sample: SampleSelection,
) -> list[str]:
    """Compare every RETAINED derived QID/pageid set in a
    ``discovery_manifest.json`` document against freshly recomputed values.
    """
    mismatches: list[str] = []
    stored_overlap = discovery_manifest.get("overlap_sets", {})
    checks: list[tuple[str, list[str], frozenset[str]]] = [
        (
            "accepted_direct_qid_overlap",
            sorted(overlap_sets.accepted_direct_qid_overlap, key=qid_sort_key),
            overlap_sets.accepted_direct_qid_overlap,
        ),
        (
            "retained_alternative_qid_overlap",
            sorted(overlap_sets.retained_alternative_qid_overlap, key=qid_sort_key),
            overlap_sets.retained_alternative_qid_overlap,
        ),
        (
            "incremental_qid_lead",
            sorted(overlap_sets.incremental_qid_lead, key=qid_sort_key),
            overlap_sets.incremental_qid_lead,
        ),
    ]
    for key, expected_qids, expected_set in checks:
        stored = stored_overlap.get(key, {})
        if stored.get("qids") != expected_qids:
            mismatches.append(f"overlap_sets.{key}.qids does not match the recomputed set")
        if stored.get("count") != len(expected_set):
            mismatches.append(
                f"overlap_sets.{key}.count={stored.get('count')!r} != recomputed {len(expected_set)!r}"
            )
    stored_no_qid = stored_overlap.get("no_wikidata_qid", {})
    expected_pageids = sorted(overlap_sets.no_wikidata_qid_pageids)
    if stored_no_qid.get("pageids") != expected_pageids:
        mismatches.append("overlap_sets.no_wikidata_qid.pageids does not match the recomputed set")
    if stored_no_qid.get("count") != len(overlap_sets.no_wikidata_qid_pageids):
        mismatches.append(
            f"overlap_sets.no_wikidata_qid.count={stored_no_qid.get('count')!r} != recomputed "
            f"{len(overlap_sets.no_wikidata_qid_pageids)!r}"
        )

    stored_stratum = discovery_manifest.get("primary_stratum_assignment", {})
    for stratum, qids in incremental_by_stratum.items():
        expected_qids = sorted(qids, key=qid_sort_key)
        stored = stored_stratum.get(stratum, {})
        if stored.get("qids") != expected_qids:
            mismatches.append(
                f"primary_stratum_assignment.{stratum}.qids does not match the recomputed set"
            )
        if stored.get("count") != len(expected_qids):
            mismatches.append(
                f"primary_stratum_assignment.{stratum}.count={stored.get('count')!r} != "
                f"recomputed {len(expected_qids)!r}"
            )

    stored_selection = discovery_manifest.get("sample_selection", {})
    for stratum, stratum_qids in sample.selected_by_stratum.items():
        if stored_selection.get("selected_by_stratum_sha256_order", {}).get(stratum) != list(
            stratum_qids
        ):
            mismatches.append(
                f"sample_selection.selected_by_stratum_sha256_order.{stratum} does not match the "
                "recomputed SHA256-ordered selection"
            )
    if stored_selection.get("selected_qids") != list(sample.selected_qids):
        mismatches.append("sample_selection.selected_qids does not match the recomputed set")
    if stored_selection.get("selected_count") != len(sample.selected_qids):
        mismatches.append(
            f"sample_selection.selected_count={stored_selection.get('selected_count')!r} != "
            f"recomputed {len(sample.selected_qids)!r}"
        )
    return mismatches


def verify_sample_selection_self_consistency(
    incremental_by_stratum: dict[str, frozenset[str]], sample: SampleSelection
) -> list[str]:
    """Recompute the deterministic sample selection from scratch and compare
    against *sample*: exact per-stratum cap enforcement, no cross-stratum
    backfill, and global <=150 bound.
    """
    mismatches: list[str] = []
    recomputed = select_deterministic_sample(incremental_by_stratum)
    if recomputed.selected_qids != sample.selected_qids:
        mismatches.append("sample selection is not reproducible from the retained incremental sets")
    if len(sample.selected_qids) > SAMPLE_TOTAL_CAP:
        mismatches.append(
            f"selected_count={len(sample.selected_qids)} exceeds the fixed total cap "
            f"{SAMPLE_TOTAL_CAP}"
        )
    for stratum, cap in SAMPLE_CAP_BY_STRATUM.items():
        chosen = sample.selected_by_stratum.get(stratum, ())
        if len(chosen) > cap:
            mismatches.append(
                f"selected_by_stratum[{stratum}] has {len(chosen)} entries, exceeding cap {cap}"
            )
    return mismatches


def verify_wikidata_context_coverage_self_consistency(quality_sample: dict[str, Any]) -> list[str]:
    """Independently verify that a retained ``quality_sample.json``
    document's ``wikidata_context`` rows exactly cover
    ``selection_reference.selected_qids`` — no missing, extra or duplicate
    QID — rather than trusting that the two lists were built consistently.
    """
    mismatches: list[str] = []
    selected = quality_sample.get("selection_reference", {}).get("selected_qids", [])
    selected_set = frozenset(selected)
    context_qids = [row.get("qid") for row in quality_sample.get("wikidata_context", [])]
    context_set = frozenset(context_qids)
    if len(context_qids) != len(context_set):
        duplicates = sorted({q for q in context_qids if context_qids.count(q) > 1})
        mismatches.append(f"wikidata_context contains duplicate QID(s): {duplicates}")
    if context_set != selected_set:
        missing = selected_set - context_set
        extra = context_set - selected_set
        mismatches.append(
            f"wikidata_context does not exactly cover selected_qids: missing={sorted(missing)} "
            f"extra={sorted(extra)}"
        )
    return mismatches


def recompute_rights_access_ok(
    *,
    rights_gate: dict[str, str],
    wikipedia_source: dict[str, Any],
    wikidata_source: dict[str, Any],
) -> bool:
    """Independently recompute whether SLICE-0023 rights/access were
    truthfully ALLOWED, from the reviewed Source records themselves — never
    from a retained self-declared ``quality_sample.rights_access_ok`` flag.

    Re-runs the SLICE-0007 ``research_lead`` gate live against
    *wikipedia_source* and directly reads the automated-ingestion/
    bulk-bootstrap clearance fields (mirroring exactly the checks the live
    runner performs before dispatch — see
    ``scripts/bootstrap/wikimedia_sl0023_category_leads_runner.run_live``),
    then cross-checks that the retained ``discovery_manifest.rights_gate``
    summary agrees with what was actually re-derived. A retained
    ``rights_gate`` that disagrees with the live Source records is itself
    treated as untrustworthy (returns ``False``), so a coherent tamper of
    ``rights_access_ok`` together with the stored ``rights_gate`` cannot
    silently pass.
    """
    from hullq.sources.rights import DecisionOutcome, SourceUse, check_source_use

    research_lead_decision = check_source_use(wikipedia_source, SourceUse.RESEARCH_LEAD)
    wikipedia_automated_ingestion = wikipedia_source["rights"]["clearance"]["automated_ingestion"]
    wikidata_bulk_bootstrap = wikidata_source["rights"]["clearance"]["bulk_bootstrap"]
    wikidata_automated_ingestion = wikidata_source["rights"]["clearance"]["automated_ingestion"]

    expected_rights_gate = {
        "wikipedia_research_lead": str(research_lead_decision.outcome),
        "wikipedia_automated_ingestion_clearance": wikipedia_automated_ingestion,
        "wikidata_bulk_bootstrap": wikidata_bulk_bootstrap,
        "wikidata_automated_ingestion": wikidata_automated_ingestion,
    }
    if rights_gate != expected_rights_gate:
        return False

    return (
        research_lead_decision.outcome == DecisionOutcome.ALLOWED
        and wikipedia_automated_ingestion == "allowed"
        and wikidata_bulk_bootstrap == "allowed"
        and wikidata_automated_ingestion == "allowed"
    )


def verify_quality_sample_self_consistency(
    quality_sample: dict[str, Any],
    *,
    unique_incremental_count: int,
    recomputed_rights_access_ok: bool,
) -> list[str]:
    """Recompute quality-tag totals/percentages and the mechanical
    recommendation from a retained ``quality_sample.json`` document's own
    ``quality_review`` rows, and compare against the document's stored
    summary fields.

    ``recomputed_rights_access_ok`` MUST be independently derived (via
    ``recompute_rights_access_ok``) from the live reviewed Source records and
    the retained ``discovery_manifest.rights_gate`` — never read from this
    document's own ``rights_access_ok`` field, which is untrusted input being
    verified, not a source of truth.
    """
    mismatches: list[str] = []
    if bool(quality_sample.get("rights_access_ok")) != recomputed_rights_access_ok:
        mismatches.append(
            f"rights_access_ok={quality_sample.get('rights_access_ok')!r} != independently "
            f"recomputed {recomputed_rights_access_ok!r}"
        )
    rows = quality_sample.get("quality_review", [])
    valid_tags = {str(t) for t in QualityTag}
    recomputed_counts: dict[str, int] = {str(t): 0 for t in QualityTag}
    for row in rows:
        tag = row.get("quality_tag")
        if tag not in valid_tags:
            mismatches.append(f"candidate[{row.get('qid')}].quality_tag={tag!r} is not recognized")
            continue
        if not str(row.get("rationale", "")).strip():
            mismatches.append(f"candidate[{row.get('qid')}].rationale is empty")
        recomputed_counts[tag] += 1

    selected = set(quality_sample.get("selection_reference", {}).get("selected_qids", []))
    reviewed = {row.get("qid") for row in rows}
    if selected != reviewed:
        mismatches.append("quality_review does not exactly cover selection_reference.selected_qids")

    if recomputed_counts != quality_sample.get("quality_tag_counts"):
        mismatches.append(
            f"quality_tag_counts={quality_sample.get('quality_tag_counts')!r} != recomputed "
            f"{recomputed_counts!r}"
        )
    total_sampled = len(rows)
    if quality_sample.get("total_sampled") != total_sampled:
        mismatches.append(
            f"total_sampled={quality_sample.get('total_sampled')!r} != recomputed {total_sampled!r}"
        )
    recomputed_pct = {
        tag: round((count / total_sampled * 100.0) if total_sampled else 0.0, 4)
        for tag, count in recomputed_counts.items()
    }
    if recomputed_pct != quality_sample.get("quality_tag_percentages"):
        mismatches.append("quality_tag_percentages does not match the recomputed percentages")

    recomputed_recommendation = str(
        determine_recommendation(
            rights_access_ok=recomputed_rights_access_ok,
            unique_incremental_count=unique_incremental_count,
            quality_tag_counts=recomputed_counts,
        )
    )
    if quality_sample.get("recommendation") != recomputed_recommendation:
        mismatches.append(
            f"recommendation={quality_sample.get('recommendation')!r} != recomputed "
            f"{recomputed_recommendation!r}"
        )
    if quality_sample.get("unique_incremental_qid_lead_count") != unique_incremental_count:
        mismatches.append(
            "unique_incremental_qid_lead_count="
            f"{quality_sample.get('unique_incremental_qid_lead_count')!r} != actual "
            f"{unique_incremental_count!r}"
        )
    return mismatches


def reconstruct_unique_pages_from_manifest(
    discovery_manifest: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    """Reconstruct the ``page_id -> {title, canonical_url, categories, qid}``
    mapping from a retained ``discovery_manifest.json`` document's own
    ``unique_pages`` block, for fully offline recompute of every downstream
    derived measurement.
    """
    result: dict[int, dict[str, Any]] = {}
    for pid_str, info in discovery_manifest.get("unique_pages", {}).items():
        result[int(pid_str)] = {
            "title": info["title"],
            "canonical_url": info["canonical_url"],
            "categories": tuple(info["categories"]),
            "qid": info.get("qid"),
        }
    return result


def verify_unique_pages_reconstruction_self_consistency(
    discovery_manifest: dict[str, Any],
) -> list[str]:
    """Rebuild the consolidated unique-page mapping purely from the retained
    per-category ``members`` lists (never from the document's own
    ``unique_pages`` summary block) and compare title/canonical_url/categories
    against that summary block exactly, so a tampered ``unique_pages`` block
    cannot silently validate itself.
    """
    mismatches: list[str] = []
    rebuilt = build_unique_pages(discovery_manifest.get("categories", {}))
    stored = discovery_manifest.get("unique_pages", {})
    rebuilt_pids = set(rebuilt)
    stored_pids = {int(pid_str) for pid_str in stored}
    if rebuilt_pids != stored_pids:
        mismatches.append(
            "unique_pages page-ID set does not match the set rebuilt from categories.*.members"
        )
    for pid, info in rebuilt.items():
        stored_row = stored.get(str(pid), {})
        if stored_row.get("title") != info["title"]:
            mismatches.append(f"unique_pages[{pid}].title does not match the rebuilt value")
        if stored_row.get("canonical_url") != info["canonical_url"]:
            mismatches.append(f"unique_pages[{pid}].canonical_url does not match the rebuilt value")
        if tuple(stored_row.get("categories", ())) != info["categories"]:
            mismatches.append(f"unique_pages[{pid}].categories does not match the rebuilt value")
    return mismatches


def verify_title_signal_rows_self_consistency(
    discovery_manifest: dict[str, Any],
    unique_pages: dict[int, dict[str, Any]],
    overlap_sets: OverlapSets,
    accepted_label_index: dict[str, frozenset[str]],
) -> list[str]:
    """Recompute the exact title-signal category for every unique page
    outside ``accepted_direct_qid_overlap`` and compare against the retained
    ``title_signal.rows``/``title_signal.totals``.
    """
    mismatches: list[str] = []
    expected_pageids = {
        pid
        for pid, info in unique_pages.items()
        if info.get("qid") not in overlap_sets.accepted_direct_qid_overlap
    }
    stored_rows = {
        row["pageid"]: row for row in discovery_manifest.get("title_signal", {}).get("rows", [])
    }
    if set(stored_rows) != expected_pageids:
        mismatches.append("title_signal.rows page-ID coverage does not match the recomputed set")

    recomputed_totals: dict[str, int] = {str(c): 0 for c in TitleSignalCategory}
    for pid in expected_pageids:
        info = unique_pages[pid]
        category, owners = classify_title_signal(
            info["title"], accepted_label_index=accepted_label_index
        )
        recomputed_totals[str(category)] += 1
        row = stored_rows.get(pid)
        if row is None:
            continue
        if row.get("title_signal_category") != str(category):
            mismatches.append(
                f"title_signal.rows[{pid}].title_signal_category={row.get('title_signal_category')!r} "
                f"!= recomputed {category!r}"
            )
        if tuple(row.get("owner_qids", ())) != owners:
            mismatches.append(
                f"title_signal.rows[{pid}].owner_qids does not match the recomputed value"
            )

    if recomputed_totals != discovery_manifest.get("title_signal", {}).get("totals"):
        mismatches.append("title_signal.totals does not match the recomputed totals")
    return mismatches
