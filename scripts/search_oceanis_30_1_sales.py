"""SLICE-0038 Owning.pro real sales-offer pilot — local owner-test command.

Proves, locally and fail-closed, the first real HullQ product loop:

    technical Search input (locked Q10, "Draft <= 1.60 m")
    -> matching real BoatDesign / resolved configuration
       (unchanged SLICE-0037 BENETEAU Oceanis 30.1 projection + Search kernel)
    -> one explicitly permitted market-data API (Owning.pro public read API)
    -> current real sales listings
    -> independent BoatDesign identity match (never search-return membership)
    -> listing-level configuration assessment (never design-level inheritance)
    -> visible sales-offer output

This script does not duplicate the Search kernel: Required Behavior A is
proved by literally invoking `scripts.search_oceanis_30_1.
load_oceanis_30_1_configuration_set` / `load_locked_queries` and
`hullq.search.configuration_engine.run_configuration_query`, the same
functions and retained projection SLICE-0037 uses. Required Behavior E reuses
`hullq.search.criteria.evaluate_numeric_leaf` against the *exact* Q10
`NumericLeafCriterion` extracted from the locked query -- the listing-level
draft threshold is never re-typed as a second literal.

Run (live, the primary owner-test path):
    uv run python scripts/search_oceanis_30_1_sales.py --live

Run (offline replay of the retained 2026-08-31 sample, used by CI/tests):
    uv run python scripts/search_oceanis_30_1_sales.py

See `research/market/sl0038-owning-oceanis-30-1/REPORT.md` for the bounded
source-access disposition and full research narrative.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    # Allows `uv run python scripts/search_oceanis_30_1_sales.py` to resolve the
    # sibling `scripts.search_oceanis_30_1` module the same way pytest already
    # does (pytest adds ROOT via rootdir insertion); a no-op when already present.
    sys.path.insert(0, str(ROOT))

from hullq.search.configuration_engine import (  # noqa: E402
    DesignQueryEvaluation,
    run_configuration_query,
)
from hullq.search.criteria import NumericLeafCriterion, evaluate_numeric_leaf  # noqa: E402
from hullq.search.types import ReasonCode, ResultClass, TruthState  # noqa: E402
from hullq.search.values import (  # noqa: E402
    QualifiedNumericValue,
    ValueQualification,
    is_finite_real_number,
)
from scripts.search_oceanis_30_1 import (  # noqa: E402
    DEEP_KEEL,
    RETRACTABLE_KEEL,
    SHALLOW_KEEL,
    load_locked_queries,
    load_oceanis_30_1_configuration_set,
)

RETAINED_SAMPLE_PATH = (
    ROOT
    / "research"
    / "market"
    / "sl0038-owning-oceanis-30-1"
    / "owning_oceanis_30_1_sample.v1.json"
)

EXPECTED_DESIGN_ID: Final = "beneteau-oceanis-30-1"
Q10_QUERY_ID: Final = "Q10"

OWNING_PLATFORM: Final = "Owning"
OWNING_API_BASE: Final = "https://api.owning.pro"
OWNING_LISTING_SEARCH_PATH: Final = "/api/listings"
OWNING_WEB_LISTING_URL_TEMPLATE: Final = "https://owning.pro/en/listings/{slug}"
OWNING_QUERY_CATEGORY: Final = "sailboats"
OWNING_QUERY_TEXT: Final = "Oceanis 30.1"
OWNING_QUERY_LIMIT: Final = 20  # slice hard cap: at most 20 returned candidates considered

_AGGREGATOR_SELLER_NAME: Final = "Owning Marketplace"


class RegressionError(RuntimeError):
    """Raised when the unchanged SLICE-0037 Q10 path no longer holds.

    Per slice Required Behavior A: "If SLICE-0037 no longer produces this
    accepted result on the implementation HEAD, stop and report the
    regression rather than implementing around it." This script never
    catches this exception to substitute a different result.
    """


class OwningQueryError(RuntimeError):
    """Raised when the Owning API response cannot be interpreted safely."""


# ---------------------------------------------------------------------------
# Required Behavior A — run the real design Search first
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DesignSearchProof:
    """Independently-verified SLICE-0037 Q10 result this script is allowed to use."""

    is_fixture: bool
    evaluation: DesignQueryEvaluation
    draft_criterion: NumericLeafCriterion


def run_design_search_first() -> DesignSearchProof:
    """Invoke the unchanged SLICE-0037 Q10 path and independently re-verify it.

    Never sets a BoatDesign ID directly -- everything below is derived from
    actually running `run_configuration_query`, exactly as
    `scripts/search_oceanis_30_1.py` does. Raises `RegressionError` (rather
    than silently substituting a hardcoded result) if any of the five facts
    slice Required Behavior A requires no longer hold.
    """
    config_set = load_oceanis_30_1_configuration_set()
    queries = load_locked_queries()
    q10_entries = [q for q in queries if q[0] == Q10_QUERY_ID]
    if len(q10_entries) != 1:
        raise RegressionError(
            f"expected exactly one {Q10_QUERY_ID} entry in the locked query fixture; "
            f"found {len(q10_entries)}"
        )
    _, _role, _description, query = q10_entries[0]

    draft_criteria = [
        c
        for c in query.criteria
        if isinstance(c, NumericLeafCriterion) and c.field == "draft_max_m"
    ]
    if len(draft_criteria) != 1:
        raise RegressionError(
            f"expected exactly one draft_max_m NumericLeafCriterion in {Q10_QUERY_ID}; "
            f"found {len(draft_criteria)}"
        )
    draft_criterion = draft_criteria[0]

    outcome = run_configuration_query(query, [config_set])
    all_evaluations = (
        outcome.confirmed_matches + outcome.confirmed_non_matches + outcome.insufficient_data
    )
    if len(all_evaluations) != 1:
        raise RegressionError(
            f"expected exactly one design (Oceanis 30.1) evaluated for {Q10_QUERY_ID}; "
            f"got {len(all_evaluations)}"
        )
    evaluation = all_evaluations[0]

    if config_set.is_fixture is not False:
        raise RegressionError(
            f"real Oceanis projection must be is_fixture=False; got {config_set.is_fixture!r}"
        )
    if evaluation.result_class is not ResultClass.CONFIRMED_MATCH:
        raise RegressionError(
            f"{Q10_QUERY_ID} no longer CONFIRMED_MATCH on this HEAD; "
            f"got {evaluation.result_class.value}"
        )
    if tuple(evaluation.matching_configuration_ids) != (SHALLOW_KEEL,):
        raise RegressionError(
            f"{Q10_QUERY_ID} matching_configuration_ids regressed; expected exactly "
            f"({SHALLOW_KEEL!r},), got {evaluation.matching_configuration_ids!r}"
        )
    truths = {ce.configuration_id: ce.truth for ce in evaluation.configuration_evaluations}
    if truths.get(DEEP_KEEL) is not TruthState.FALSE:
        raise RegressionError(
            f"{Q10_QUERY_ID} {DEEP_KEEL} truth regressed; expected FALSE, "
            f"got {truths.get(DEEP_KEEL)!r}"
        )
    if truths.get(RETRACTABLE_KEEL) is not TruthState.UNKNOWN:
        raise RegressionError(
            f"{Q10_QUERY_ID} {RETRACTABLE_KEEL} truth regressed; expected UNKNOWN, "
            f"got {truths.get(RETRACTABLE_KEEL)!r}"
        )

    return DesignSearchProof(
        is_fixture=config_set.is_fixture, evaluation=evaluation, draft_criterion=draft_criterion
    )


# ---------------------------------------------------------------------------
# Required Behavior B — live/offline Owning candidate retrieval
# ---------------------------------------------------------------------------


def fetch_owning_candidates_live() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One bounded live GET against the documented Owning search endpoint.

    Returns the raw candidate list (already bounded to `OWNING_QUERY_LIMIT`
    by the request itself) plus a small access-metadata record for Required
    Behavior F / the completion report. No authentication is used: Owning's
    current documentation states public `GET` listing/search endpoints
    require none (re-checked 2026-08-31; see REPORT.md).
    """
    import httpx  # local import: --live is the only path that needs a network client

    params = {
        "category": OWNING_QUERY_CATEGORY,
        "q": OWNING_QUERY_TEXT,
        "limit": OWNING_QUERY_LIMIT,
    }
    accessed_at = datetime.now(UTC).isoformat()
    with httpx.Client(
        base_url=OWNING_API_BASE,
        timeout=20.0,
        headers={
            "User-Agent": "HullQ-SLICE-0038-pilot/1 (bounded, non-recurring; contact via repository)"
        },
    ) as client:
        response = client.get(OWNING_LISTING_SEARCH_PATH, params=params)
    response.raise_for_status()
    payload = response.json()
    results = payload.get("results")
    if not isinstance(results, list):
        raise OwningQueryError(
            f"Owning {OWNING_LISTING_SEARCH_PATH} response missing a 'results' list"
        )
    access_metadata = {
        "endpoint": f"{OWNING_API_BASE}{OWNING_LISTING_SEARCH_PATH}",
        "query_params": params,
        "accessed_at": accessed_at,
        "http_status": response.status_code,
        "pagination": payload.get("pagination"),
    }
    return results[:OWNING_QUERY_LIMIT], access_metadata


def load_owning_candidates_offline(
    path: Path = RETAINED_SAMPLE_PATH,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Deterministic offline replay of the retained real 2026-08-31 sample.

    Used as this script's default mode and by CI: no network access, and the
    data is the exact (trimmed) real live capture, not a synthetic fixture --
    see the retained file's own `note` field.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    results = list(payload["results"])
    access_metadata = {
        "endpoint": f"{payload['source_api_base']}{payload['source_endpoint']}",
        "query_params": payload["source_query_params"],
        "accessed_at": payload["accessed_at"],
        "http_status": 200,
        "pagination": payload.get("pagination"),
        "replay_of_retained_sample": str(path),
    }
    return results[:OWNING_QUERY_LIMIT], access_metadata


# ---------------------------------------------------------------------------
# Required Behavior D — independent BoatDesign identity admission
# ---------------------------------------------------------------------------

_EXPECTED_BRAND_TOKEN: Final = "beneteau"
_EXPECTED_MODEL_TOKEN: Final = "oceanis301"


def _normalize_identity_token(value: str | None) -> str:
    """Case/accent/punctuation-insensitive token for exact identity comparison.

    Deliberately not fuzzy: this collapses formatting noise only (case,
    accents, dots, spaces, hyphens) so "Oceanis 30.1", "OCEANIS 30.1" and the
    scraper-mangled "Oceanis 301" / "Oceanis 30 1" all reduce to the same
    token, while distinct models ("Oceanis 30", "Oceanis 31", "Oceanis 300",
    "Oceanis 34.1") remain distinct strings after normalization -- no digit
    is ever inserted, dropped or reinterpreted.
    """
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.lower())


def admit_boat_design_identity(manufacturer: str | None, model: str | None) -> str | None:
    """Independently authorize `matched_boat_design_id` from structured identity only.

    Small closed exact-match oracle for this one pilot design (Required
    Behavior D): never consulted merely because a listing was present in an
    Owning search-return set, never fuzzy, never a generic entity-resolution
    subsystem. Requires the normalized brand token to be exactly "beneteau"
    and the normalized model token -- after stripping one leading duplicated
    brand prefix, a real quirk observed in `boat24.com`-sourced records -- to
    be exactly "oceanis301". Any other value, including a near-neighbor model
    (Oceanis 30, 31, 300, 34.1, ...), yields `None` (unresolved).
    """
    brand_token = _normalize_identity_token(manufacturer)
    if brand_token != _EXPECTED_BRAND_TOKEN:
        return None
    model_token = _normalize_identity_token(model)
    if model_token.startswith(brand_token):
        model_token = model_token[len(brand_token) :]
    if model_token != _EXPECTED_MODEL_TOKEN:
        return None
    return EXPECTED_DESIGN_ID


def _extract_raw_identity(listing: dict[str, Any]) -> dict[str, str | None]:
    """Structured brand/model only -- title/description are never consulted here.

    `attributes.model`/`attributes.brand` (Owning's own dedicated asset-type
    fields, `GET /api/asset-types/boats`) are preferred; `boat_specs.brand`/
    `boat_specs.model` (the raw upstream-scrape mirror) are the fallback. A
    listing exposing neither yields `model=None`, which
    `admit_boat_design_identity` always rejects -- title is deliberately not
    parsed as a third fallback (would edge into generic free-text entity
    resolution, which this pilot does not authorize; see REPORT.md for the
    three real 2026-08-31 candidates this actually excluded).
    """
    attributes = listing.get("attributes") or {}
    boat_specs = listing.get("boat_specs") or {}
    manufacturer = attributes.get("brand") or boat_specs.get("brand")
    model = attributes.get("model") or boat_specs.get("model")
    return {"manufacturer": manufacturer, "model": model, "variant": None}


# ---------------------------------------------------------------------------
# Required Behavior E — listing-level configuration assessment
# ---------------------------------------------------------------------------


def _structured_draft_observations(listing: dict[str, Any]) -> list[Any]:
    """Every *structured* numeric draft observation on *listing* -- never free text.

    Reads only the dedicated `attributes.draft` field (`GET
    /api/asset-types/boats`) and the scraped `boat_specs.specs.dimensions`
    draft-shaped keys. Title/description text is never parsed for words like
    "deep"/"standard"/"shoal"/"shallow"/"lifting"/"swing" -- the addendum's
    "no automatic configuration synonym table" rule -- so this function
    cannot manufacture a value that was never structurally present.
    """
    observations: list[Any] = []
    attributes = listing.get("attributes") or {}
    if "draft" in attributes:
        observations.append(attributes["draft"])
    dimensions = ((listing.get("boat_specs") or {}).get("specs") or {}).get("dimensions") or {}
    observations.extend(dimensions[key] for key in ("draft_m", "draft") if key in dimensions)
    return observations


def qualify_listing_draft(listing: dict[str, Any]) -> tuple[QualifiedNumericValue, str]:
    """Independently qualify the *offered physical boat's* own draft.

    Never the design's / model's draft (addendum #2). Fail-closed per slice
    Required Behavior E and the binding pre-start addendum:

    - no structured observation at all -> `MISSING` (UNKNOWN, no evidence);
    - every observation nonphysical/malformed (<=0, boolean, non-finite,
      non-numeric) -> `MISSING`, and a `0` is never passed to the comparator
      (addendum #1) -- `is_finite_real_number` also rejects `bool` (a
      subclass of `int` in Python) and NaN/+-Infinity;
    - two or more *admissible* observations that materially disagree ->
      `UNRESOLVED_CONFLICT` (addendum #3), even when some raw observations
      were independently rejected as nonphysical first;
    - one or more identical admissible observations -> `CONFIRMED` with that
      shared value (addendum #8).
    """
    raw_observations = _structured_draft_observations(listing)
    if not raw_observations:
        return (
            QualifiedNumericValue(value=None, qualification=ValueQualification.MISSING),
            "no structured listing-specific draft attribute is present on this listing",
        )

    admissible: list[float] = []
    rejected: list[Any] = []
    for obs in raw_observations:
        if is_finite_real_number(obs) and obs > 0:
            admissible.append(float(obs))
        else:
            rejected.append(obs)

    if not admissible:
        return (
            QualifiedNumericValue(value=None, qualification=ValueQualification.MISSING),
            f"listing-specific draft observation(s) {raw_observations!r} are nonphysical/"
            f"malformed (zero, negative, boolean or non-finite) and were not passed to the "
            f"Search comparator",
        )

    distinct = sorted(set(admissible))
    if len(distinct) > 1:
        return (
            QualifiedNumericValue(value=None, qualification=ValueQualification.UNRESOLVED_CONFLICT),
            f"listing-specific draft observations {distinct} materially conflict; "
            f"not resolved to a single value",
        )

    value = distinct[0]
    evidence = f"listing-specific structured draft observation = {value} m"
    if rejected:
        evidence += f" (rejected nonphysical/malformed observation(s) {rejected!r})"
    return QualifiedNumericValue(value=value, qualification=ValueQualification.CONFIRMED), evidence


# ---------------------------------------------------------------------------
# Required Behavior C — canonical listing normalization
# ---------------------------------------------------------------------------


def _extract_year(listing: dict[str, Any]) -> int | None:
    attributes = listing.get("attributes") or {}
    year = attributes.get("year")
    if year is None:
        year = (listing.get("boat_specs") or {}).get("year")
    if not isinstance(year, int) or isinstance(year, bool):
        return None
    return year


def _map_seller(seller: dict[str, Any]) -> dict[str, str | None]:
    """Owning's own `seller.type` vocabulary (agent/human) has no member that maps

    onto the canonical schema's broker/dealer/private/unknown vocabulary, so
    this pilot always reports `type="unknown"` rather than guessing. All ten
    real 2026-08-31 candidates additionally shared one literal aggregator
    placeholder account (`"Owning Marketplace"`) that is not a genuine seller
    identity -- retaining it as if it were the boat's actual seller/broker
    would misrepresent an automated aggregation pipeline as a person/business,
    so that specific name is dropped to `None` rather than retained.
    """
    name = seller.get("name")
    if name == _AGGREGATOR_SELLER_NAME:
        name = None
    return {"name": name, "type": "unknown"}


def normalize_listing(listing: dict[str, Any], observed_at: str) -> dict[str, Any]:
    """Build the MARKET_LISTING_SCHEMA.v0.1.json-shaped canonical record for *listing*."""
    raw_identity = _extract_raw_identity(listing)
    matched_boat_design_id = admit_boat_design_identity(
        raw_identity["manufacturer"], raw_identity["model"]
    )
    price = listing.get("price") or {}
    location = listing.get("location") or {}
    seller = listing.get("seller") or {}
    return {
        "platform": OWNING_PLATFORM,
        "source_listing_id": listing.get("id"),
        "url": OWNING_WEB_LISTING_URL_TEMPLATE.format(slug=listing["slug"]),
        "title": listing.get("title"),
        "observed_at": observed_at,
        "raw_identity": raw_identity,
        "matched_boat_design_id": matched_boat_design_id,
        "year": _extract_year(listing),
        "price": {"amount": price.get("amount"), "currency": price.get("currency")},
        "location": {"text": location.get("city"), "country_code": location.get("country")},
        "seller": _map_seller(seller),
    }


# ---------------------------------------------------------------------------
# Assembly — one candidate at a time
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AssessedOffer:
    """One identity-admitted Oceanis 30.1 canonical listing plus its own truth."""

    listing: dict[str, Any]
    truth: TruthState
    reason: ReasonCode | None
    evidence: str


@dataclass(frozen=True, slots=True)
class UnresolvedCandidate:
    """A raw Owning candidate whose BoatDesign identity could not be admitted."""

    raw_identity: dict[str, str | None]
    title: str | None
    slug: str | None


def assess_candidate(
    raw_listing: dict[str, Any], observed_at: str, draft_criterion: NumericLeafCriterion
) -> AssessedOffer | UnresolvedCandidate:
    """Identity admission first; listing-level draft truth only for admitted offers.

    Required Behavior D: search-return membership alone is irrelevant here --
    `normalize_listing` calls the independent `admit_boat_design_identity`
    oracle without ever knowing the candidate came back from an
    Oceanis-30.1-targeted query. Required Behavior E: the design-level Q10
    match is never consulted for the offered boat's own truth; only
    `qualify_listing_draft`'s listing-specific evidence feeds
    `evaluate_numeric_leaf`.
    """
    canonical = normalize_listing(raw_listing, observed_at)
    if canonical["matched_boat_design_id"] is None:
        return UnresolvedCandidate(
            raw_identity=canonical["raw_identity"],
            title=canonical["title"],
            slug=raw_listing.get("slug"),
        )
    qualified, evidence = qualify_listing_draft(raw_listing)
    criterion_eval = evaluate_numeric_leaf(draft_criterion, qualified)
    return AssessedOffer(
        listing=canonical,
        truth=criterion_eval.truth,
        reason=criterion_eval.reason,
        evidence=evidence,
    )


# ---------------------------------------------------------------------------
# Owner-test surface
# ---------------------------------------------------------------------------


def _print_design_search_proof(proof: DesignSearchProof) -> None:
    print(
        f"\n[1] Technical Search input: {Q10_QUERY_ID} — draft_max_m <= "
        f"{proof.draft_criterion.threshold_max} m (unchanged SLICE-0037 locked query)"
    )
    print(
        f"[2] Design Search result: design_id={proof.evaluation.design_id} "
        f"result_class={proof.evaluation.result_class.value} "
        f"matching_configuration_ids={list(proof.evaluation.matching_configuration_ids)} "
        f"(is_fixture={proof.is_fixture})"
    )
    for ce in proof.evaluation.configuration_evaluations:
        print(f"      configuration={ce.configuration_id} truth={ce.truth.value}")
    print(f"DESIGN MATCH: Oceanis 30.1 has a Q10-matching factory configuration ({SHALLOW_KEEL})")


def _print_offer(offer: AssessedOffer) -> None:
    listing = offer.listing
    price = listing["price"]
    location = listing["location"]
    reason = f" reason={offer.reason.value}" if offer.reason is not None else ""
    print(f"\n  - {listing['title']}  ({listing['url']})")
    print(
        f"      year={listing['year']} price={price['amount']} {price['currency']} "
        f"location={location['text']}, {location['country_code']}"
    )
    print(f"      matched_boat_design_id={listing['matched_boat_design_id']}")
    print("      LISTING CONFIG: independently assessed from this physical listing only")
    print(f"      listing_config_truth={offer.truth.value}{reason} evidence={offer.evidence}")


def run_owner_test(live: bool) -> int:
    design_proof = run_design_search_first()
    _print_design_search_proof(design_proof)

    if live:
        raw_candidates, access_metadata = fetch_owning_candidates_live()
        mode = "LIVE"
    else:
        raw_candidates, access_metadata = load_owning_candidates_offline()
        mode = "OFFLINE (retained 2026-08-31 sample replay)"

    print(
        f"\n[3] Live market source: {OWNING_PLATFORM} — {access_metadata['endpoint']} — mode={mode}"
    )
    print(f"      query_params={access_metadata['query_params']}")
    print(f"[4] Owning candidate listings received: {len(raw_candidates)}")

    observed_at = access_metadata["accessed_at"]
    offers: list[AssessedOffer] = []
    unresolved: list[UnresolvedCandidate] = []
    for raw in raw_candidates:
        result = assess_candidate(raw, observed_at, design_proof.draft_criterion)
        if isinstance(result, AssessedOffer):
            offers.append(result)
        else:
            unresolved.append(result)

    print(f"\n[5] Normalized current Oceanis 30.1 offers (identity-admitted): {len(offers)}")
    print("[6] Per-offer assessment:")
    for offer in offers:
        _print_offer(offer)

    if unresolved:
        print(
            f"\n  Identity-unresolved candidates (not counted as Oceanis 30.1 offers): {len(unresolved)}"
        )
        for u in unresolved:
            print(f"    - {u.title!r} (slug={u.slug}) raw_identity={u.raw_identity}")

    true_count = sum(1 for o in offers if o.truth is TruthState.TRUE)
    false_count = sum(1 for o in offers if o.truth is TruthState.FALSE)
    unknown_count = sum(1 for o in offers if o.truth is TruthState.UNKNOWN)

    print("\n[7] Summary:")
    print(f"      candidates_received={len(raw_candidates)}")
    print(f"      identity_admitted_offers={len(offers)}")
    print(f"      identity_unresolved_candidates={len(unresolved)}")
    print(f"      TRUE={true_count} FALSE={false_count} UNKNOWN={unknown_count}")

    if not offers:
        print(
            "\nBLOCKED: zero current Oceanis 30.1 offers were admitted from Owning for this "
            "bounded query. This is not a software defect -- the product proof is not "
            "demonstrated for this run."
        )
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Query the real Owning.pro public read API instead of replaying the retained sample.",
    )
    args = parser.parse_args(argv)
    return run_owner_test(live=args.live)


if __name__ == "__main__":
    sys.exit(main())
