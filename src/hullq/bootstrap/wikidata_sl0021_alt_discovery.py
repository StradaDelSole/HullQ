"""Alternative Wikidata sailboat-class discovery-semantics pilot — SLICE-0021.

Implements the pure, deterministic measurement logic described in
``docs/slices/SLICE-0021-wikidata-alternative-sailboat-class-discovery-pilot.md``.

This module performs no network acquisition (that lives in
``hullq.sources.wikidata``) and no database access. Given already-acquired
route QID sets and, later, sampled entity detail records, it:

- defines the exact four fixed live query routes (R0-R3);
- fingerprints and hard-asserts the accepted immutable SLICE-0017/0018 inputs
  (1,829 retained direct-discovery QIDs, 1,770 accepted AUTO_ADMIT universe);
- measures current-R0 drift against the retained 1,829-QID universe,
  separately from alternative-route incremental yield;
- computes each alternative route's incremental yield against **current R0**
  (never only the historical 1,829 set);
- computes pairwise/cross-route overlap and each route's unique contribution;
- selects a deterministic, hard-capped entity-detail sample
  (<=75/route, <=200 unique globally, ordered by numeric QID);
  - classifies sampled candidates' identity signal using ONLY exact
  QID-overlap and exact (``strip().casefold()``) label/alias comparison
  against the accepted 1,770 universe — no fuzzy/heuristic matching;
- derives a non-binding, evidence-only disposition per alternative route.

Explicitly does NOT:
- create, modify or delete any canonical HullQ row;
- mint a HullQ ID for any incremental candidate;
- modify the accepted SLICE-0017/0018 retained manifests;
- change the production Wikidata adapter's default discovery query;
- treat an R3 candidate's description text as proof of correct classification;
- perform any normalization beyond surrounding-whitespace trim + casefold.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

__all__ = [
    "ACCEPTED_AUTO_ADMIT_COUNT",
    "ACCEPTED_SL0017_MANIFEST_SHA256",
    "ACCEPTED_SL0018_MANIFEST_SHA256",
    "R0",
    "R1",
    "R2",
    "R3",
    "RETAINED_DIRECT_DISCOVERY_COUNT",
    "ROUTES",
    "ROUTE_ALT_IDS",
    "ROUTE_HARD_LIMIT",
    "SAMPLE_CAP_GLOBAL",
    "SAMPLE_CAP_PER_ROUTE",
    "AcceptedIdentity",
    "AcceptedUniverse",
    "CrossRouteOverlap",
    "DriftResult",
    "IdentitySignalCategory",
    "ImmutableInputIntegrityError",
    "Route",
    "RouteDisposition",
    "SampleCompletenessError",
    "SampleSelection",
    "build_accepted_label_index",
    "build_accepted_universe",
    "build_discovery_probe_document",
    "build_route_record",
    "build_sampled_candidates_document",
    "classify_identity_signal",
    "compute_cross_route_overlap",
    "compute_incremental_yield",
    "compute_query_sha256",
    "compute_r0_drift",
    "determine_route_disposition",
    "load_and_fingerprint_immutable_inputs",
    "normalize_exact",
    "qid_list_digest",
    "qid_sort_key",
    "select_entity_detail_sample",
    "verify_accepted_universe_reference_self_consistency",
    "verify_discovery_probe_derived_sets_self_consistency",
    "verify_immutable_inputs_self_consistency",
    "verify_route_record_self_consistency",
    "verify_sample_entity_detail_completeness",
    "verify_sampled_candidates_self_consistency",
]

# ---------------------------------------------------------------------------
# Fixed bounds
# ---------------------------------------------------------------------------

ROUTE_HARD_LIMIT = 3000
SAMPLE_CAP_PER_ROUTE = 75
SAMPLE_CAP_GLOBAL = 200

# Accepted immutable historical measurements this slice must hard-assert
# before any live acquisition (docs/slices/SLICE-0021-*.md "Immutable
# historical comparison inputs"). These MUST NOT change; a drifted retained
# artifact fails closed via ImmutableInputIntegrityError.
RETAINED_DIRECT_DISCOVERY_COUNT = 1829
ACCEPTED_AUTO_ADMIT_COUNT = 1770

ACCEPTED_SL0017_MANIFEST_SHA256 = "076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845"
ACCEPTED_SL0018_MANIFEST_SHA256 = "41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f"

ROOT = Path(__file__).resolve().parents[3]
SL0017_MANIFEST_PATH = ROOT / "research" / "bootstrap" / "wikidata" / "manifest.json"
SL0018_MANIFEST_PATH = (
    ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json"
)


class ImmutableInputIntegrityError(RuntimeError):
    """Raised when a retained SLICE-0017/0018 input artifact no longer
    reproduces its accepted historical fingerprint/counts.

    SLICE-0021 MUST fail closed (BLOCKED) rather than silently measure
    alternative-route yield against a drifted immutable input.
    """


# ---------------------------------------------------------------------------
# Fixed route definitions — exactly R0-R3, byte-identical to the controlling
# slice document. No additional route may be added.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Route:
    """One fixed, precommitted SLICE-0021 live query route."""

    route_id: str
    version: str
    query_text: str


R0 = Route(
    route_id="current_direct_control",
    version="SLICE-0021-R0-v1",
    query_text=(
        "SELECT DISTINCT ?item WHERE {\n"
        "  ?item wdt:P31 wd:Q106179098 .\n"
        "}\n"
        "ORDER BY ?item\n"
        "LIMIT 3000\n"
    ),
)

R1 = Route(
    route_id="sailboat_class_closure",
    version="SLICE-0021-R1-v1",
    query_text=(
        "SELECT DISTINCT ?item WHERE {\n"
        "  ?item wdt:P31/wdt:P279* wd:Q106179098 .\n"
        "}\n"
        "ORDER BY ?item\n"
        "LIMIT 3000\n"
    ),
)

R2 = Route(
    route_id="legacy_sailboat_class_closure",
    version="SLICE-0021-R2-v1",
    query_text=(
        "SELECT DISTINCT ?item WHERE {\n"
        "  ?item wdt:P31/wdt:P279* wd:Q57303455 .\n"
        "}\n"
        "ORDER BY ?item\n"
        "LIMIT 3000\n"
    ),
)

R3 = Route(
    route_id="misclassified_sailboat_class_description",
    version="SLICE-0021-R3-v1",
    query_text=(
        "SELECT DISTINCT ?item ?desc WHERE {\n"
        "  ?item wdt:P31 wd:Q1075310 .\n"
        "  ?item schema:description ?desc .\n"
        '  FILTER (lang(?desc) = "en")\n'
        '  FILTER CONTAINS(?desc, "sailboat class")\n'
        "}\n"
        "ORDER BY ?item\n"
        "LIMIT 3000\n"
    ),
)

ROUTES: tuple[Route, ...] = (R0, R1, R2, R3)


def compute_query_sha256(route: Route) -> str:
    """Deterministic SHA256 digest of a route's exact query text."""
    return hashlib.sha256(route.query_text.encode("utf-8")).hexdigest()


def qid_sort_key(qid: str) -> int:
    """Numeric sort key for a Wikidata QID (``Q123`` -> ``123``).

    Required by the controlling slice's entity-detail-sample selection rule
    ("deterministic sample selection by numeric QID order") — a plain string
    sort would order ``Q10`` before ``Q9``.
    """
    return int(qid[1:])


def qid_list_digest(qids: Sequence[str]) -> str:
    """Deterministic digest of a full bounded returned QID set, in the exact
    retained order (already deterministic via each route's ``ORDER BY ?item``
    plus ``LIMIT``).
    """
    return hashlib.sha256("\n".join(qids).encode("utf-8")).hexdigest()


def _assert_no_duplicates(qids: Sequence[str], *, context: str) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for qid in qids:
        if qid in seen:
            duplicates.add(qid)
        seen.add(qid)
    if duplicates:
        raise ValueError(
            f"{context}: duplicate QID(s) in a SELECT DISTINCT result: {sorted(duplicates)}"
        )


def build_route_record(
    route: Route,
    qids: Sequence[str],
    *,
    acquired_at: str,
    http_request_count: int,
    throttle_count: int = 0,
    retry_count: int = 0,
    error_count: int = 0,
    malformed_response_count: int = 0,
    item_descriptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build one retained per-route acquisition record (R0-R3 alike).

    ``qids`` MUST already be the full bounded (<=``ROUTE_HARD_LIMIT``)
    deterministic result of dispatching *route*'s exact query; this function
    performs no network access itself. Fails closed on a duplicate QID (a
    ``SELECT DISTINCT`` result must never contain one) or on a result
    exceeding the shared hard limit.

    ``item_descriptions`` (R3 only) preserves the raw ``schema:description``
    text keyed by QID, purely as review evidence — it is never used to
    authorize classification.
    """
    qid_list = list(qids)
    _assert_no_duplicates(qid_list, context=f"route {route.route_id!r}")
    if len(qid_list) > ROUTE_HARD_LIMIT:
        raise ValueError(
            f"route {route.route_id!r} returned {len(qid_list)} QIDs, exceeding the hard "
            f"limit of {ROUTE_HARD_LIMIT}"
        )
    record: dict[str, Any] = {
        "route_id": route.route_id,
        "version": route.version,
        "query_text": route.query_text,
        "query_sha256": compute_query_sha256(route),
        "hard_limit": ROUTE_HARD_LIMIT,
        "result_count": len(qid_list),
        "possibly_truncated": len(qid_list) >= ROUTE_HARD_LIMIT,
        "qids": qid_list,
        "qid_list_digest": qid_list_digest(qid_list),
        "acquired_at": acquired_at,
        "http_request_count": http_request_count,
        "throttle_count": throttle_count,
        "retry_count": retry_count,
        "error_count": error_count,
        "malformed_response_count": malformed_response_count,
    }
    if item_descriptions is not None:
        record["item_descriptions"] = dict(sorted(item_descriptions.items()))
    return record


# ---------------------------------------------------------------------------
# Immutable input loading + fingerprinting (SLICE-0017 + SLICE-0018 manifests)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AcceptedIdentity:
    """One accepted AUTO_ADMIT identity's retained QID + label + aliases,
    used only for the exact identity-signal probe — never for canonical
    mutation.
    """

    qid: str
    label: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class AcceptedUniverse:
    """The immutable accepted SLICE-0017/0018 comparison universe, loaded and
    fingerprinted once before any live acquisition.
    """

    sl0017_manifest_path: str
    sl0017_sha256: str
    sl0018_manifest_path: str
    sl0018_sha256: str
    retained_direct_discovery_qids: frozenset[str]
    accepted_auto_admit_identities: tuple[AcceptedIdentity, ...]

    @property
    def accepted_auto_admit_qids(self) -> frozenset[str]:
        return frozenset(identity.qid for identity in self.accepted_auto_admit_identities)


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_and_fingerprint_immutable_inputs(
    sl0017_manifest_path: Path = SL0017_MANIFEST_PATH,
    sl0018_manifest_path: Path = SL0018_MANIFEST_PATH,
) -> AcceptedUniverse:
    """Load, fingerprint and hard-assert the accepted immutable SLICE-0017 +
    SLICE-0018 retained manifests, per the controlling slice's "Immutable
    historical comparison inputs" section.

    Fails closed via ``ImmutableInputIntegrityError`` before any live network
    use if either manifest's raw-byte SHA256 no longer matches the pinned
    accepted value, or if the retained direct-discovery union does not equal
    exactly ``RETAINED_DIRECT_DISCOVERY_COUNT`` (1,829), or if the combined
    AUTO_ADMIT universe does not equal exactly ``ACCEPTED_AUTO_ADMIT_COUNT``
    (1,770). Never writes to either manifest file.
    """
    import json

    sl0017_bytes = sl0017_manifest_path.read_bytes()
    sl0017_sha256 = hashlib.sha256(sl0017_bytes).hexdigest()
    if sl0017_sha256 != ACCEPTED_SL0017_MANIFEST_SHA256:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0017 manifest at {sl0017_manifest_path} failed integrity check: "
            f"sha256={sl0017_sha256!r}, expected {ACCEPTED_SL0017_MANIFEST_SHA256!r}"
        )
    sl0017_manifest = json.loads(sl0017_bytes.decode("utf-8"))

    sl0018_bytes = sl0018_manifest_path.read_bytes()
    sl0018_sha256 = hashlib.sha256(sl0018_bytes).hexdigest()
    if sl0018_sha256 != ACCEPTED_SL0018_MANIFEST_SHA256:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0018 manifest at {sl0018_manifest_path} failed integrity check: "
            f"sha256={sl0018_sha256!r}, expected {ACCEPTED_SL0018_MANIFEST_SHA256!r}"
        )
    sl0018_manifest = json.loads(sl0018_bytes.decode("utf-8"))

    sl0017_qids = {row["qid"] for row in sl0017_manifest["candidates"]}
    sl0018_delta_qids = {row["qid"] for row in sl0018_manifest["candidates"]}
    overlap = sl0017_qids & sl0018_delta_qids
    if overlap:
        raise ImmutableInputIntegrityError(
            f"Retained SLICE-0017 baseline and SLICE-0018 delta manifests unexpectedly share "
            f"{len(overlap)} QID(s); the delta must be disjoint from the baseline by construction."
        )
    retained_direct_discovery_qids = frozenset(sl0017_qids | sl0018_delta_qids)
    if len(retained_direct_discovery_qids) != RETAINED_DIRECT_DISCOVERY_COUNT:
        raise ImmutableInputIntegrityError(
            "Retained direct-discovery universe does not equal the accepted "
            f"{RETAINED_DIRECT_DISCOVERY_COUNT}: got {len(retained_direct_discovery_qids)}"
        )

    identities: list[AcceptedIdentity] = []
    for row in (*sl0017_manifest["candidates"], *sl0018_manifest["candidates"]):
        if row["decision"] != "auto_admit":
            continue
        identities.append(
            AcceptedIdentity(
                qid=row["qid"],
                label=row["preferred_label"],
                aliases=tuple(row.get("aliases") or ()),
            )
        )
    if len(identities) != ACCEPTED_AUTO_ADMIT_COUNT:
        raise ImmutableInputIntegrityError(
            "Combined accepted AUTO_ADMIT universe does not equal the accepted "
            f"{ACCEPTED_AUTO_ADMIT_COUNT}: got {len(identities)}"
        )

    return AcceptedUniverse(
        sl0017_manifest_path=_repo_relative(sl0017_manifest_path),
        sl0017_sha256=sl0017_sha256,
        sl0018_manifest_path=_repo_relative(sl0018_manifest_path),
        sl0018_sha256=sl0018_sha256,
        retained_direct_discovery_qids=retained_direct_discovery_qids,
        accepted_auto_admit_identities=tuple(identities),
    )


def build_accepted_universe(
    *,
    retained_direct_discovery_qids: frozenset[str],
    accepted_auto_admit_identities: Sequence[AcceptedIdentity],
    sl0017_manifest_path: str = "<in-memory>",
    sl0017_sha256: str = "",
    sl0018_manifest_path: str = "<in-memory>",
    sl0018_sha256: str = "",
) -> AcceptedUniverse:
    """Build an ``AcceptedUniverse`` directly from already-known values, with
    NO accepted-constant/fingerprint integrity enforcement.

    Used by tests that exercise drift/incremental/identity-signal logic
    against a small synthetic universe rather than the full accepted
    1,829/1,770 artifacts — every production/CI code path uses
    ``load_and_fingerprint_immutable_inputs`` instead.
    """
    return AcceptedUniverse(
        sl0017_manifest_path=sl0017_manifest_path,
        sl0017_sha256=sl0017_sha256,
        sl0018_manifest_path=sl0018_manifest_path,
        sl0018_sha256=sl0018_sha256,
        retained_direct_discovery_qids=retained_direct_discovery_qids,
        accepted_auto_admit_identities=tuple(accepted_auto_admit_identities),
    )


# ---------------------------------------------------------------------------
# R0 current-direct drift measurement (separate from alternative-route yield)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriftResult:
    """Current R0 drift versus the retained historical direct-discovery
    universe. MUST NOT be added to R1/R2/R3 incremental yield.
    """

    retained_direct_count: int
    current_direct_count: int
    retained_direct_still_present_count: int
    retained_direct_absent_now_count: int
    new_current_direct_since_sl0018_count: int
    retained_direct_absent_now_qids: tuple[str, ...]
    new_current_direct_since_sl0018_qids: tuple[str, ...]


def compute_r0_drift(
    retained_direct_discovery_qids: frozenset[str], current_r0_qids: Sequence[str]
) -> DriftResult:
    """Compare the current R0 (control) result against the retained
    historical direct-discovery universe (accepted at exactly 1,829 QIDs).
    """
    current_set = frozenset(current_r0_qids)
    still_present = retained_direct_discovery_qids & current_set
    absent_now = retained_direct_discovery_qids - current_set
    new_since = current_set - retained_direct_discovery_qids
    return DriftResult(
        retained_direct_count=len(retained_direct_discovery_qids),
        current_direct_count=len(current_set),
        retained_direct_still_present_count=len(still_present),
        retained_direct_absent_now_count=len(absent_now),
        new_current_direct_since_sl0018_count=len(new_since),
        retained_direct_absent_now_qids=tuple(sorted(absent_now, key=qid_sort_key)),
        new_current_direct_since_sl0018_qids=tuple(sorted(new_since, key=qid_sort_key)),
    )


# ---------------------------------------------------------------------------
# Alternative-route incremental yield (measured against CURRENT R0)
# ---------------------------------------------------------------------------


def compute_incremental_yield(
    route_qids: Sequence[str], current_r0_qids: Sequence[str]
) -> frozenset[str]:
    """An alternative route's incremental yield: route QIDs minus CURRENT R0
    QIDs (never merely the historical 1,829 set — see controlling slice
    "Core semantic rules" #1-2 and each route's own "incremental yield"
    definition).
    """
    return frozenset(route_qids) - frozenset(current_r0_qids)


@dataclass(frozen=True)
class CrossRouteOverlap:
    """Pairwise overlap and unique per-route contribution among the
    alternative routes' (R1/R2/R3) incremental-yield sets.
    """

    pairwise: dict[tuple[str, str], frozenset[str]]
    total_union: frozenset[str]
    unique_contribution: dict[str, frozenset[str]]


def compute_cross_route_overlap(
    incremental_by_route: dict[str, frozenset[str]],
) -> CrossRouteOverlap:
    """Compute pairwise overlap, total alternative-route union, and each
    route's unique contribution (its incremental QIDs not shared by any other
    alternative route), from a mapping of route_id -> incremental QID set.
    """
    route_ids = sorted(incremental_by_route)
    pairwise: dict[tuple[str, str], frozenset[str]] = {}
    for i, a in enumerate(route_ids):
        for b in route_ids[i + 1 :]:
            pairwise[(a, b)] = incremental_by_route[a] & incremental_by_route[b]

    total_union: frozenset[str] = frozenset()
    for qids in incremental_by_route.values():
        total_union |= qids

    unique_contribution: dict[str, frozenset[str]] = {}
    for rid, qids in incremental_by_route.items():
        others: frozenset[str] = frozenset()
        for other_rid, other_qids in incremental_by_route.items():
            if other_rid != rid:
                others |= other_qids
        unique_contribution[rid] = qids - others

    return CrossRouteOverlap(
        pairwise=pairwise, total_union=total_union, unique_contribution=unique_contribution
    )


# ---------------------------------------------------------------------------
# Bounded, deterministic entity-detail sample selection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SampleSelection:
    """The deterministic, hard-capped entity-detail sample selection.

    ``selected_qids`` is the final globally-capped (<=``SAMPLE_CAP_GLOBAL``)
    sample, in ascending numeric QID order. ``route_membership`` records,
    for every selected QID, which alternative route(s) it is genuinely
    incremental for (computed from each route's FULL incremental set, not
    only its own <=75-capped subset) — a QID sampled via one route's cap may
    still also be incremental for another route.
    """

    selected_qids: tuple[str, ...]
    route_membership: dict[str, frozenset[str]]
    per_route_pre_global_cap: dict[str, tuple[str, ...]]


def select_entity_detail_sample(
    incremental_by_route: dict[str, frozenset[str]],
) -> SampleSelection:
    """Deterministically select the bounded entity-detail sample.

    Each route's incremental-yield set is independently capped at
    ``SAMPLE_CAP_PER_ROUTE`` (75) by ascending numeric QID order; the union of
    those capped sets (overlapping QIDs counting once) is then further capped
    at ``SAMPLE_CAP_GLOBAL`` (200), again by ascending numeric QID order.
    """
    per_route_capped: dict[str, tuple[str, ...]] = {}
    pool: set[str] = set()
    for rid, qids in incremental_by_route.items():
        ordered = tuple(sorted(qids, key=qid_sort_key)[:SAMPLE_CAP_PER_ROUTE])
        per_route_capped[rid] = ordered
        pool.update(ordered)

    pool_sorted = sorted(pool, key=qid_sort_key)
    selected = tuple(pool_sorted[:SAMPLE_CAP_GLOBAL])
    selected_set = frozenset(selected)

    route_membership = {
        rid: frozenset(q for q in qids if q in selected_set)
        for rid, qids in incremental_by_route.items()
    }
    return SampleSelection(
        selected_qids=selected,
        route_membership=route_membership,
        per_route_pre_global_cap=per_route_capped,
    )


# ---------------------------------------------------------------------------
# Exact-only identity-signal classification
# ---------------------------------------------------------------------------


def normalize_exact(value: str) -> str:
    """The ONLY allowed identity-signal string normalization: surrounding-
    whitespace trim + casefold. No internal-whitespace collapsing, punctuation
    rewriting, manufacturer-prefix manipulation, token reordering, abbreviation
    expansion or fuzzy/edit-distance matching may ever be applied here.
    """
    return value.strip().casefold()


def build_accepted_label_index(
    identities: Sequence[AcceptedIdentity],
) -> dict[str, frozenset[str]]:
    """Build the exact-normalized label/alias -> owning-QID-set index for the
    accepted AUTO_ADMIT universe, used only for the exact identity-signal
    probe (never for canonical mutation).
    """
    index: dict[str, set[str]] = {}
    for identity in identities:
        for raw in (identity.label, *identity.aliases):
            if not raw:
                continue
            key = normalize_exact(raw)
            index.setdefault(key, set()).add(identity.qid)
    return {key: frozenset(qids) for key, qids in index.items()}


class IdentitySignalCategory(StrEnum):
    """The four research-only identity-signal categories (controlling
    slice's "Exact identity-signal check").
    """

    ACCEPTED_QID_OVERLAP = "accepted_qid_overlap"
    EXACT_IDENTITY_SIGNAL_OTHER_QID = "exact_identity_signal_other_qid"
    NO_EXACT_IDENTITY_SIGNAL = "no_exact_identity_signal"
    UNRESOLVED_EXACT_IDENTITY_SIGNAL = "unresolved_exact_identity_signal"


def classify_identity_signal(
    qid: str,
    label: str | None,
    aliases: Sequence[str],
    *,
    accepted_qids: frozenset[str],
    accepted_label_index: dict[str, frozenset[str]],
) -> tuple[IdentitySignalCategory, tuple[str, ...]]:
    """Classify one sampled candidate's identity signal against the accepted
    universe, in the mandated order: exact QID overlap first, then (only for
    QIDs not already accepted) exact normalized label/alias signals.

    Returns ``(category, owner_qids)`` where ``owner_qids`` is the sampled
    QID itself for ``ACCEPTED_QID_OVERLAP``, the empty tuple for
    ``NO_EXACT_IDENTITY_SIGNAL``, and the sorted accepted owner QID(s)
    otherwise. Two or more distinct accepted owners for the same exact
    normalized signal classify as ``UNRESOLVED_EXACT_IDENTITY_SIGNAL`` rather
    than forcing a choice.
    """
    if qid in accepted_qids:
        return IdentitySignalCategory.ACCEPTED_QID_OVERLAP, (qid,)

    owners: set[str] = set()
    candidates: list[str] = ([label] if label else []) + list(aliases)
    for raw in candidates:
        key = normalize_exact(raw)
        owners |= accepted_label_index.get(key, frozenset())

    if not owners:
        return IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL, ()
    if len(owners) > 1:
        return IdentitySignalCategory.UNRESOLVED_EXACT_IDENTITY_SIGNAL, tuple(sorted(owners))
    return IdentitySignalCategory.EXACT_IDENTITY_SIGNAL_OTHER_QID, tuple(sorted(owners))


# ---------------------------------------------------------------------------
# Evidence-derived (non-binding) route disposition
# ---------------------------------------------------------------------------


class RouteDisposition(StrEnum):
    """One evidence-derived disposition per alternative route. A recommendation
    only — never production authorization (controlling slice
    "Result/disposition vocabulary").
    """

    NO_INCREMENTAL_YIELD = "NO_INCREMENTAL_YIELD"
    RESEARCH_ONLY_SIGNAL = "RESEARCH_ONLY_SIGNAL"
    FOLLOWUP_DISCOVERY_CANDIDATE = "FOLLOWUP_DISCOVERY_CANDIDATE"


# Sampled-candidate identity-signal categories that indicate the incremental
# yield may contain genuinely new (or ambiguous) identity rather than merely
# an alternate discovery path to already-accepted HullQ identities.
_NOVEL_SIGNAL_CATEGORIES = frozenset(
    {
        IdentitySignalCategory.EXACT_IDENTITY_SIGNAL_OTHER_QID,
        IdentitySignalCategory.UNRESOLVED_EXACT_IDENTITY_SIGNAL,
        IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL,
    }
)


def determine_route_disposition(
    incremental_count: int,
    sample_categories: Sequence[IdentitySignalCategory],
) -> RouteDisposition:
    """Derive one route's evidence-only disposition.

    ``NO_INCREMENTAL_YIELD`` when the route found no QID outside current R0.
    Otherwise ``RESEARCH_ONLY_SIGNAL`` when every sampled incremental
    candidate turned out to be an exact QID-overlap with an already-accepted
    identity (i.e. the route is merely an alternate path to already-known
    HullQ identities, not evidence of new ones); ``FOLLOWUP_DISCOVERY_CANDIDATE``
    when at least one sampled candidate shows a non-overlap signal (a
    genuinely new, other-QID-matching, or ambiguous identity signal). This is
    a recommendation only, never automatic production authorization, and it
    NEVER overrides the R3 fail-closed review-bound rule.
    """
    if incremental_count == 0:
        return RouteDisposition.NO_INCREMENTAL_YIELD
    if any(category in _NOVEL_SIGNAL_CATEGORIES for category in sample_categories):
        return RouteDisposition.FOLLOWUP_DISCOVERY_CANDIDATE
    return RouteDisposition.RESEARCH_ONLY_SIGNAL


# ---------------------------------------------------------------------------
# Retained document assembly — JSON-primitive, pure (no network/DB access)
# ---------------------------------------------------------------------------

DISCOVERY_PROBE_SCHEMA_VERSION = "sl0021-discovery-probe-v1"
SAMPLED_CANDIDATES_SCHEMA_VERSION = "sl0021-sampled-candidates-v1"

# Short audit labels for the three alternative (non-control) routes, in the
# fixed order the controlling slice presents them.
ROUTE_ALT_IDS: tuple[str, ...] = ("R1", "R2", "R3")

R3_FAIL_CLOSED_NOTICE = (
    "Every R3 (misclassified_sailboat_class_description) candidate remains a "
    "review/repair signal only in SLICE-0021 regardless of its identity-signal "
    "category or description quality. R3 membership never directly authorizes "
    "canonical admission or a production classification rule; a structured "
    "English description containing 'sailboat class' does not itself prove the "
    "item is correctly modeled as a HullQ BoatModel."
)

NO_EXACT_SIGNAL_NOTICE = (
    "no_exact_identity_signal means only that this bounded exact probe found no "
    "exact QID/label/alias signal. It does not prove global novelty, does not "
    "prove no corresponding HullQ identity exists, and does not authorize "
    "canonical admission."
)


def build_discovery_probe_document(
    *,
    generated_at: str,
    source_id: str,
    rights_gate: dict[str, str],
    accepted_universe: AcceptedUniverse,
    route_records: dict[str, dict[str, Any]],
    drift: DriftResult,
    incremental_by_route: dict[str, frozenset[str]],
    cross_route_overlap: CrossRouteOverlap,
) -> dict[str, Any]:
    """Assemble the retained ``discovery_probe.json`` document.

    ``route_records`` MUST be keyed by ``"R0"``..``"R3"`` and built via
    ``build_route_record``. ``incremental_by_route`` and
    ``cross_route_overlap`` MUST cover exactly ``ROUTE_ALT_IDS`` (R1-R3).
    """
    if set(route_records) != {"R0", *ROUTE_ALT_IDS}:
        raise ValueError(
            f"route_records must be keyed by exactly R0..R3; got {sorted(route_records)}"
        )
    if set(incremental_by_route) != set(ROUTE_ALT_IDS):
        raise ValueError(
            f"incremental_by_route must be keyed by exactly {ROUTE_ALT_IDS}; "
            f"got {sorted(incremental_by_route)}"
        )

    pairwise_list = [
        {"routes": [a, b], "count": len(qids), "qids": sorted(qids, key=qid_sort_key)}
        for (a, b), qids in sorted(cross_route_overlap.pairwise.items())
    ]
    unique_contribution = {
        rid: {
            "count": len(qids),
            "qids": sorted(qids, key=qid_sort_key),
        }
        for rid, qids in cross_route_overlap.unique_contribution.items()
    }

    return {
        "schema_version": DISCOVERY_PROBE_SCHEMA_VERSION,
        "generated_at": generated_at,
        "source_id": source_id,
        "rights_gate": dict(rights_gate),
        "immutable_inputs": {
            "sl0017_manifest": {
                "path": accepted_universe.sl0017_manifest_path,
                "sha256": accepted_universe.sl0017_sha256,
            },
            "sl0018_manifest": {
                "path": accepted_universe.sl0018_manifest_path,
                "sha256": accepted_universe.sl0018_sha256,
            },
            "retained_direct_discovery_count": len(
                accepted_universe.retained_direct_discovery_qids
            ),
            "accepted_auto_admit_count": len(accepted_universe.accepted_auto_admit_identities),
        },
        "routes": {rid: route_records[rid] for rid in ("R0", *ROUTE_ALT_IDS)},
        "drift": {
            "retained_direct_count": drift.retained_direct_count,
            "current_direct_count": drift.current_direct_count,
            "retained_direct_still_present_count": drift.retained_direct_still_present_count,
            "retained_direct_absent_now_count": drift.retained_direct_absent_now_count,
            "new_current_direct_since_sl0018_count": drift.new_current_direct_since_sl0018_count,
            "retained_direct_absent_now_qids": list(drift.retained_direct_absent_now_qids),
            "new_current_direct_since_sl0018_qids": list(
                drift.new_current_direct_since_sl0018_qids
            ),
        },
        "incremental": {
            rid: {
                "count": len(qids),
                "qids": sorted(qids, key=qid_sort_key),
            }
            for rid, qids in incremental_by_route.items()
        },
        "cross_route_overlap": {
            "pairwise": pairwise_list,
            "total_union_count": len(cross_route_overlap.total_union),
            "total_union_qids": sorted(cross_route_overlap.total_union, key=qid_sort_key),
            "unique_contribution": unique_contribution,
        },
    }


def build_sampled_candidates_document(
    *,
    generated_at: str,
    accepted_universe: AcceptedUniverse,
    sample: SampleSelection,
    candidate_rows: list[dict[str, Any]],
    route_dispositions: dict[str, str],
) -> dict[str, Any]:
    """Assemble the retained ``sampled_candidates.json`` document.

    ``candidate_rows`` are already-built per-candidate JSON rows (qid, route
    membership, label/aliases/description, P31/P279/P176/P287 QID lists,
    identity-signal category + owner QIDs) — this function only aggregates
    totals/selection metadata, it does not compute identity signals itself.
    """
    if set(route_dispositions) != set(ROUTE_ALT_IDS):
        raise ValueError(
            f"route_dispositions must be keyed by exactly {ROUTE_ALT_IDS}; "
            f"got {sorted(route_dispositions)}"
        )

    category_totals: dict[str, int] = {str(c): 0 for c in IdentitySignalCategory}
    for row in candidate_rows:
        category_totals[row["identity_signal_category"]] += 1

    return {
        "schema_version": SAMPLED_CANDIDATES_SCHEMA_VERSION,
        "generated_at": generated_at,
        "selection": {
            "cap_per_route": SAMPLE_CAP_PER_ROUTE,
            "cap_global": SAMPLE_CAP_GLOBAL,
            "per_route_pre_global_cap": {
                rid: list(qids) for rid, qids in sample.per_route_pre_global_cap.items()
            },
            "selected_qids": list(sample.selected_qids),
            "selected_count": len(sample.selected_qids),
        },
        "accepted_universe_reference": {
            "sl0017_sha256": accepted_universe.sl0017_sha256,
            "sl0018_sha256": accepted_universe.sl0018_sha256,
            "accepted_auto_admit_count": len(accepted_universe.accepted_auto_admit_identities),
        },
        "candidates": candidate_rows,
        "category_totals": category_totals,
        "route_dispositions": dict(route_dispositions),
        "r3_fail_closed_notice": R3_FAIL_CLOSED_NOTICE,
        "no_exact_signal_notice": NO_EXACT_SIGNAL_NOTICE,
    }


# ---------------------------------------------------------------------------
# Fail-closed completeness check — live entity-detail fetch vs selected sample
# ---------------------------------------------------------------------------


class SampleCompletenessError(RuntimeError):
    """Raised when the live entity-detail fetch for the selected SLICE-0021
    sample does not exactly cover the selected sample QID set.

    A missing, duplicate, or unexpected QID in the ``wbgetentities`` response
    (including a QID silently absent because it resolved to a non-item or
    missing entity) MUST fail the run closed before any retained document is
    written, rather than silently persist a partial or contaminated sample —
    mirrors the accepted SLICE-0018 ``DeltaCompletenessError`` /
    ``verify_entity_acquisition_completeness`` contract.
    """


def verify_sample_entity_detail_completeness(
    selected_qids: Sequence[str], fetched_qids: Sequence[str]
) -> None:
    """Fail closed unless *fetched_qids* covers *selected_qids* exactly.

    Checks, before any candidate-row or document assembly uses the fetched
    entity details:

    - no selected QID is missing from the fetched QIDs (including a QID that
      silently resolved to a non-item or absent entity);
    - no unexpected QID appears among the fetched QIDs;
    - no QID is fetched more than once.

    Callers pass the plain QID list extracted from the adapter's
    ``fetch_sampled_entity_details`` result (``[d.qid for d in details]``);
    this function stays decoupled from ``hullq.sources.wikidata`` so it
    remains pure/offline-testable.
    """
    selected_set = set(selected_qids)
    fetched_list = list(fetched_qids)
    fetched_set = set(fetched_list)

    duplicates = {qid for qid in fetched_set if fetched_list.count(qid) > 1}
    missing = selected_set - fetched_set
    unexpected = fetched_set - selected_set

    if duplicates or missing or unexpected:
        raise SampleCompletenessError(
            "Entity-detail fetch did not exactly cover the selected SLICE-0021 sample "
            f"(selected={len(selected_set)}, fetched={len(fetched_list)}): "
            f"missing={sorted(missing, key=qid_sort_key)} "
            f"unexpected={sorted(unexpected, key=qid_sort_key)} "
            f"duplicates={sorted(duplicates, key=qid_sort_key)}. Refusing to retain a "
            "partial/contaminated entity-detail sample."
        )


# ---------------------------------------------------------------------------
# Offline self-consistency verification of already-retained documents
# ---------------------------------------------------------------------------
#
# These functions recompute every structurally-derivable field of a retained
# discovery_probe.json / sampled_candidates.json document from the document's
# OWN retained raw facts (QID lists, candidate rows) plus the fixed R0-R3
# route definitions and a freshly (re-)loaded AcceptedUniverse — never from
# the document's own already-computed summary fields — so a tampered summary
# field cannot silently validate itself. Each returns a list of
# human-readable mismatch descriptions; an empty list means fully
# self-consistent. Pure and offline: no network access.

_ROUTE_BY_KEY: dict[str, Route] = {"R0": R0, "R1": R1, "R2": R2, "R3": R3}


def verify_route_record_self_consistency(route_key: str, record: dict[str, Any]) -> list[str]:
    """Recompute one retained route record's ``route_id``/``version``/
    ``query_text``/``query_sha256``/``result_count``/``hard_limit``/
    ``possibly_truncated``/``qid_list_digest`` from the fixed route
    definition for *route_key* and the record's own retained ``qids`` list.
    """
    if route_key not in _ROUTE_BY_KEY:
        return [f"unknown route key {route_key!r}"]
    expected = _ROUTE_BY_KEY[route_key]
    mismatches: list[str] = []

    if record.get("route_id") != expected.route_id:
        mismatches.append(
            f"{route_key}.route_id={record.get('route_id')!r} != expected {expected.route_id!r}"
        )
    if record.get("version") != expected.version:
        mismatches.append(
            f"{route_key}.version={record.get('version')!r} != expected {expected.version!r}"
        )
    if record.get("query_text") != expected.query_text:
        mismatches.append(f"{route_key}.query_text does not match the fixed route definition")

    expected_sha256 = compute_query_sha256(expected)
    if record.get("query_sha256") != expected_sha256:
        mismatches.append(
            f"{route_key}.query_sha256={record.get('query_sha256')!r} != recomputed "
            f"{expected_sha256!r}"
        )

    qids = record.get("qids", [])
    if len(qids) != len(set(qids)):
        mismatches.append(f"{route_key}.qids contains duplicate QID(s)")
    if record.get("result_count") != len(qids):
        mismatches.append(
            f"{route_key}.result_count={record.get('result_count')!r} != len(qids)={len(qids)}"
        )
    if record.get("hard_limit") != ROUTE_HARD_LIMIT:
        mismatches.append(
            f"{route_key}.hard_limit={record.get('hard_limit')!r} != {ROUTE_HARD_LIMIT}"
        )
    expected_truncated = len(qids) >= ROUTE_HARD_LIMIT
    if record.get("possibly_truncated") != expected_truncated:
        mismatches.append(
            f"{route_key}.possibly_truncated={record.get('possibly_truncated')!r} != "
            f"expected {expected_truncated!r}"
        )
    expected_digest = qid_list_digest(qids)
    if record.get("qid_list_digest") != expected_digest:
        mismatches.append(
            f"{route_key}.qid_list_digest={record.get('qid_list_digest')!r} != recomputed "
            f"{expected_digest!r}"
        )
    return mismatches


def verify_immutable_inputs_self_consistency(
    immutable_inputs: dict[str, Any], accepted_universe: AcceptedUniverse
) -> list[str]:
    """Compare a retained ``discovery_probe.json`` document's
    ``immutable_inputs`` block against a freshly (re-)loaded
    ``AcceptedUniverse`` (typically from ``load_and_fingerprint_immutable_inputs``,
    which already fails closed on its own if the loaded universe itself has
    drifted from the accepted SHA256/1,829/1,770 constants).

    Also independently re-asserts the accepted-constant counts here as
    defense-in-depth: a caller supplying an ``AcceptedUniverse`` built by any
    other path (bypassing the fail-closed loader) still cannot pass this
    check with a wrong-sized universe.
    """
    mismatches: list[str] = []
    sl0017 = immutable_inputs.get("sl0017_manifest", {})
    sl0018 = immutable_inputs.get("sl0018_manifest", {})
    if sl0017.get("sha256") != accepted_universe.sl0017_sha256:
        mismatches.append(
            f"immutable_inputs.sl0017_manifest.sha256={sl0017.get('sha256')!r} != actual "
            f"loaded {accepted_universe.sl0017_sha256!r}"
        )
    if sl0018.get("sha256") != accepted_universe.sl0018_sha256:
        mismatches.append(
            f"immutable_inputs.sl0018_manifest.sha256={sl0018.get('sha256')!r} != actual "
            f"loaded {accepted_universe.sl0018_sha256!r}"
        )

    actual_direct_count = len(accepted_universe.retained_direct_discovery_qids)
    retained_direct_discovery_count = immutable_inputs.get("retained_direct_discovery_count")
    if retained_direct_discovery_count != actual_direct_count:
        mismatches.append(
            f"immutable_inputs.retained_direct_discovery_count={retained_direct_discovery_count!r} "
            f"!= actual loaded {actual_direct_count!r}"
        )
    if actual_direct_count != RETAINED_DIRECT_DISCOVERY_COUNT:
        mismatches.append(
            f"actual loaded retained_direct_discovery_count={actual_direct_count!r} != accepted "
            f"constant {RETAINED_DIRECT_DISCOVERY_COUNT!r}"
        )

    actual_auto_admit_count = len(accepted_universe.accepted_auto_admit_identities)
    accepted_auto_admit_count = immutable_inputs.get("accepted_auto_admit_count")
    if accepted_auto_admit_count != actual_auto_admit_count:
        mismatches.append(
            f"immutable_inputs.accepted_auto_admit_count={accepted_auto_admit_count!r} != "
            f"actual loaded {actual_auto_admit_count!r}"
        )
    if actual_auto_admit_count != ACCEPTED_AUTO_ADMIT_COUNT:
        mismatches.append(
            f"actual loaded accepted_auto_admit_count={actual_auto_admit_count!r} != accepted "
            f"constant {ACCEPTED_AUTO_ADMIT_COUNT!r}"
        )
    return mismatches


def verify_discovery_probe_derived_sets_self_consistency(
    discovery_probe: dict[str, Any],
    *,
    drift: DriftResult,
    incremental_by_route: dict[str, frozenset[str]],
    cross_route_overlap: CrossRouteOverlap,
) -> list[str]:
    """Compare every RETAINED derived QID set/list in a ``discovery_probe.json``
    document against freshly recomputed values, exactly — not merely by count.

    The round-1 amendment's self-consistency checks recomputed structural
    fields (route identity, immutable-input references, sampled-candidate
    selection/membership/category totals) but only compared drift and
    incremental-yield COUNTS, leaving the retained ``drift.*_qids``,
    ``incremental.<route>.qids``, and ``cross_route_overlap`` QID lists
    checked only indirectly. This function closes that gap.

    Callers pass *drift*/*incremental_by_route*/*cross_route_overlap* already
    recomputed (via ``compute_r0_drift``/``compute_incremental_yield``/
    ``compute_cross_route_overlap``) from the document's OWN retained
    per-route ``qids`` lists — this function only checks that the document's
    recorded derived fields exactly match those recomputations, serialized in
    the same deterministic ascending-numeric-QID order used by
    ``build_discovery_probe_document``.
    """
    mismatches: list[str] = []

    stored_drift = discovery_probe.get("drift", {})
    if stored_drift.get("retained_direct_count") != drift.retained_direct_count:
        mismatches.append(
            f"drift.retained_direct_count={stored_drift.get('retained_direct_count')!r} != "
            f"recomputed {drift.retained_direct_count!r}"
        )
    expected_absent = list(drift.retained_direct_absent_now_qids)
    if stored_drift.get("retained_direct_absent_now_qids") != expected_absent:
        mismatches.append("drift.retained_direct_absent_now_qids does not match the recomputed set")
    expected_new = list(drift.new_current_direct_since_sl0018_qids)
    if stored_drift.get("new_current_direct_since_sl0018_qids") != expected_new:
        mismatches.append(
            "drift.new_current_direct_since_sl0018_qids does not match the recomputed set"
        )

    stored_incremental = discovery_probe.get("incremental", {})
    for rid, qids in incremental_by_route.items():
        expected_qids = sorted(qids, key=qid_sort_key)
        stored = stored_incremental.get(rid, {})
        if stored.get("qids") != expected_qids:
            mismatches.append(f"incremental.{rid}.qids does not match the recomputed set")
        if stored.get("count") != len(expected_qids):
            mismatches.append(
                f"incremental.{rid}.count={stored.get('count')!r} != "
                f"recomputed {len(expected_qids)!r}"
            )

    stored_cross = discovery_probe.get("cross_route_overlap", {})
    expected_pairwise: dict[tuple[str, ...], frozenset[str]] = {
        tuple(sorted(k)): v for k, v in cross_route_overlap.pairwise.items()
    }
    stored_pairwise_list = stored_cross.get("pairwise", [])
    seen_pair_keys: set[tuple[str, ...]] = set()
    for entry in stored_pairwise_list:
        routes = entry.get("routes", [])
        pair_key = tuple(sorted(routes))
        seen_pair_keys.add(pair_key)
        expected_qids = sorted(expected_pairwise.get(pair_key, frozenset()), key=qid_sort_key)
        if entry.get("qids") != expected_qids:
            mismatches.append(
                f"cross_route_overlap.pairwise[{routes}].qids does not match the recomputed set"
            )
        if entry.get("count") != len(expected_qids):
            mismatches.append(
                f"cross_route_overlap.pairwise[{routes}].count={entry.get('count')!r} != "
                f"recomputed {len(expected_qids)!r}"
            )
    expected_pair_keys = set(expected_pairwise.keys())
    if seen_pair_keys != expected_pair_keys:
        mismatches.append(
            f"cross_route_overlap.pairwise route-pair coverage={sorted(seen_pair_keys)!r} != "
            f"expected {sorted(expected_pair_keys)!r}"
        )

    expected_union_qids = sorted(cross_route_overlap.total_union, key=qid_sort_key)
    if stored_cross.get("total_union_qids") != expected_union_qids:
        mismatches.append("cross_route_overlap.total_union_qids does not match the recomputed set")
    if stored_cross.get("total_union_count") != len(expected_union_qids):
        mismatches.append(
            f"cross_route_overlap.total_union_count={stored_cross.get('total_union_count')!r} "
            f"!= recomputed {len(expected_union_qids)!r}"
        )

    stored_unique = stored_cross.get("unique_contribution", {})
    for rid, qids in cross_route_overlap.unique_contribution.items():
        expected_qids = sorted(qids, key=qid_sort_key)
        entry = stored_unique.get(rid, {})
        if entry.get("qids") != expected_qids:
            mismatches.append(
                f"cross_route_overlap.unique_contribution.{rid}.qids does not match the "
                "recomputed set"
            )
        if entry.get("count") != len(expected_qids):
            mismatches.append(
                f"cross_route_overlap.unique_contribution.{rid}.count={entry.get('count')!r} "
                f"!= recomputed {len(expected_qids)!r}"
            )

    return mismatches


def verify_sampled_candidates_self_consistency(
    sampled_doc: dict[str, Any], incremental_by_route: dict[str, frozenset[str]]
) -> list[str]:
    """Structural self-consistency checks over a retained
    ``sampled_candidates.json`` document.

    Checks selection-count arithmetic, exact candidate-vs-selected-QID-set
    equality (no missing/extra/duplicate candidate row), every candidate's
    ``route_membership`` recomputed from the FULL (not per-route-capped)
    ``incremental_by_route`` sets, and recomputed ``category_totals``. Does
    NOT recompute identity-signal categories themselves — callers should
    additionally run ``classify_identity_signal`` per candidate for that
    (kept separate so this function needs no accepted-universe lookup).
    """
    mismatches: list[str] = []
    selection = sampled_doc.get("selection", {})
    selected_qids = selection.get("selected_qids", [])
    if selection.get("selected_count") != len(selected_qids):
        mismatches.append(
            f"selection.selected_count={selection.get('selected_count')!r} != "
            f"len(selected_qids)={len(selected_qids)}"
        )
    if len(selected_qids) != len(set(selected_qids)):
        mismatches.append("selection.selected_qids contains duplicate QID(s)")
    selected_set = frozenset(selected_qids)

    candidates = sampled_doc.get("candidates", [])
    candidate_qids = [c["qid"] for c in candidates]
    if len(candidate_qids) != len(set(candidate_qids)):
        mismatches.append("candidates contains duplicate QID row(s)")
    candidate_set = frozenset(candidate_qids)
    missing = selected_set - candidate_set
    extra = candidate_set - selected_set
    if missing:
        mismatches.append(
            f"candidates missing selected QID(s): {sorted(missing, key=qid_sort_key)}"
        )
    if extra:
        mismatches.append(
            f"candidates contains unexpected QID(s) not in selected_qids: "
            f"{sorted(extra, key=qid_sort_key)}"
        )

    for row in candidates:
        qid = row["qid"]
        expected_membership = sorted(
            rid
            for rid in ROUTE_ALT_IDS
            if qid in incremental_by_route.get(rid, frozenset()) and qid in selected_set
        )
        if row.get("route_membership") != expected_membership:
            mismatches.append(
                f"candidate[{qid}].route_membership={row.get('route_membership')!r} != "
                f"recomputed {expected_membership!r}"
            )

    recomputed_totals: dict[str, int] = {str(c): 0 for c in IdentitySignalCategory}
    for row in candidates:
        category = row.get("identity_signal_category")
        if category in recomputed_totals:
            recomputed_totals[category] += 1
    if recomputed_totals != sampled_doc.get("category_totals"):
        mismatches.append(
            f"category_totals={sampled_doc.get('category_totals')!r} != recomputed "
            f"{recomputed_totals!r}"
        )
    return mismatches


def verify_accepted_universe_reference_self_consistency(
    sampled_doc: dict[str, Any], accepted_universe: AcceptedUniverse
) -> list[str]:
    """Compare a retained ``sampled_candidates.json`` document's
    ``accepted_universe_reference`` block against a freshly (re-)loaded
    ``AcceptedUniverse`` — the sampled-candidates-side counterpart of
    ``verify_immutable_inputs_self_consistency`` (which checks the same
    facts on the ``discovery_probe.json`` side). Both documents' references
    to the accepted universe must independently agree with what was actually
    loaded; neither is treated as authoritative for the other.
    """
    mismatches: list[str] = []
    ref = sampled_doc.get("accepted_universe_reference", {})
    if ref.get("sl0017_sha256") != accepted_universe.sl0017_sha256:
        mismatches.append(
            f"accepted_universe_reference.sl0017_sha256={ref.get('sl0017_sha256')!r} != "
            f"actual loaded {accepted_universe.sl0017_sha256!r}"
        )
    if ref.get("sl0018_sha256") != accepted_universe.sl0018_sha256:
        mismatches.append(
            f"accepted_universe_reference.sl0018_sha256={ref.get('sl0018_sha256')!r} != "
            f"actual loaded {accepted_universe.sl0018_sha256!r}"
        )
    actual_auto_admit_count = len(accepted_universe.accepted_auto_admit_identities)
    if ref.get("accepted_auto_admit_count") != actual_auto_admit_count:
        mismatches.append(
            "accepted_universe_reference.accepted_auto_admit_count="
            f"{ref.get('accepted_auto_admit_count')!r} != actual loaded "
            f"{actual_auto_admit_count!r}"
        )
    return mismatches
