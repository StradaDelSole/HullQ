"""SLICE-0024 Wikimedia lead independent identity-verification pilot runner.

Two modes:

``--assemble``
    Fully offline given the retained manual research log embedded in this
    script (``RESEARCH_LOG`` below): reproduces the deterministic 18/6/6
    sample from the pinned SLICE-0023 quality sample, combines it with the
    manual research log, mechanically computes metrics/recommendation via
    ``hullq.bootstrap.wikimedia_sl0024_independent_verification``, and writes
    ``verification_sample.json``, ``verification_results.json``,
    ``REPORT.md`` and ``ARTIFACT-DIGESTS.json`` under
    ``research/bootstrap/wikimedia/sl0024-independent-verification/``.

``--verify``
    Fully offline (zero network access): reloads every already-retained
    document and recomputes every structurally-derivable field purely from
    each document's own retained raw facts, plus the artifact digests. This
    is what normal CI runs.

The manual research log itself (which pages were fetched/searched, whether
each was accessible, what discrete fact it yielded) is retained,
hand-compiled data from bounded external research performed under the
controlling slice's fixed research protocol (max 2 search queries / 4
source-page evaluations / 6 combined actions per candidate). No repository
code performs web search/browsing; this script contains no network-acquiring
code path.

Usage::

    uv run python scripts/bootstrap/wikimedia_sl0024_independent_verification_runner.py --assemble
    uv run python scripts/bootstrap/wikimedia_sl0024_independent_verification_runner.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

SL0024_DIR = ROOT / "research" / "bootstrap" / "wikimedia" / "sl0024-independent-verification"
VERIFICATION_SAMPLE_PATH = SL0024_DIR / "verification_sample.json"
VERIFICATION_SAMPLE_SCHEMA_PATH = SL0024_DIR / "verification_sample_schema.json"
VERIFICATION_RESULTS_PATH = SL0024_DIR / "verification_results.json"
VERIFICATION_RESULTS_SCHEMA_PATH = SL0024_DIR / "verification_results_schema.json"
REPORT_PATH = SL0024_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0024_DIR / "ARTIFACT-DIGESTS.json"
ARTIFACT_DIGESTS_SCHEMA_PATH = SL0024_DIR / "ARTIFACT-DIGESTS.schema.json"

GENERATED_AT = "2026-08-25T00:00:00+00:00"


def _write_json_lf(path: Path, data: Any) -> None:
    """Write JSON with a guaranteed LF-only trailing-newline byte layout,
    independent of platform newline translation, so retained artifacts are
    byte-stable across Windows/Linux CI."""
    path.write_bytes((json.dumps(data, indent=2) + "\n").encode("utf-8"))


def _write_text_lf(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def _validate_schema(instance: dict[str, Any], schema_path: Path, *, label: str) -> None:
    if not schema_path.exists():
        return
    import jsonschema

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)
    print(f"{label} schema validation: PASS", flush=True)


# ---------------------------------------------------------------------------
# Retained manual research log
#
# One entry per sampled QID. ``searches`` is the ordered list of distinct
# search/discovery queries actually issued (<=2). ``evaluations`` is the
# ordered list of distinct source-page evaluations actually performed (<=4),
# each an evidence citation: url/domain/source_class/accessible/
# supports_identity/discrete fact paraphrase/independence.
#
# ``supports_identity`` is True only when the page's own retained content
# affirmatively and directly supports this candidate's final
# subject_outcome; being accessible and in a qualifying source class alone
# does not (e.g. a manufacturer's current lineup that simply omits a
# discontinued model, or a page confirming a different, related subject).
# ---------------------------------------------------------------------------

NQ = "non_qualifying"
MFG = "manufacturer_shipyard"
DESIGNER = "designer_naval_architect"
CLASS_ASSOC = "class_association"
OWNERS_ASSOC = "owners_association"
MUSEUM = "museum_archive"
SPECIALIST = "high_quality_specialist_documentation"

TS = "2026-08-25T00:00:00Z"


def _cite(
    cid: str,
    url: str,
    domain: str,
    source_class: str,
    accessible: bool,
    supports: bool,
    fact: str,
    independent_of: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "citation_id": cid,
        "url": url,
        "domain": domain,
        "source_class": source_class,
        "access_timestamp": TS,
        "accessible": accessible,
        "supports_identity": supports,
        "discrete_fact": fact,
        "independent_of": independent_of or [],
        "research_reference_only": True,
    }


RESEARCH_LOG: dict[str, dict[str, Any]] = {
    "Q110127838": {  # S2 35
        "searches": [
            "S2 35 sailboat S2 Yachts specifications",
            "S2 Yachts owners association S2 35",
        ],
        "evaluations": [
            _cite(
                "Q110127838-c1",
                "https://sailboat.guide/s2/35",
                "sailboat.guide",
                SPECIALIST,
                False,
                False,
                "page did not render content on two attempts",
            ),
            _cite(
                "Q110127838-c2",
                "http://www.stationr.org/water/S2/S235C.htm",
                "stationr.org",
                NQ,
                True,
                False,
                "personal owner blog for hull #32, not an association/specialist publication",
            ),
            _cite(
                "Q110127838-c3",
                "https://goodoldboat.com/saildata/boat/s2-35/",
                "goodoldboat.com",
                NQ,
                False,
                False,
                "404 not found",
            ),
            _cite(
                "Q110127838-c4",
                "https://sailboat.guide/s2/35",
                "sailboat.guide",
                SPECIALIST,
                False,
                False,
                "retry, page did not render content",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "No qualifying strong or independently-corroborated specialist source was accessible within budget; the only accessible independent page was a personal owner blog, not a qualifying source class.",
    },
    "Q113428758": {  # Harbor 14
        "searches": [
            "Harbor 14 sailboat class specifications",
            "W.D. Schock Corp Harbor 14 sailboat manufacturer",
        ],
        "evaluations": [
            _cite(
                "Q113428758-c1",
                "https://wdschockcorp.com/harbor-14",
                "wdschockcorp.com",
                MFG,
                False,
                False,
                "404 not found",
            ),
            _cite(
                "Q113428758-c2",
                "https://wdschockcorp.com/about-us",
                "wdschockcorp.com",
                MFG,
                True,
                False,
                "official current model lineup lists Harbor 20/25/Santana 20/Schock 40; Harbor 14 not present (consistent with a discontinued model, not disconfirming)",
            ),
            _cite(
                "Q113428758-c3",
                "https://goodoldboat.com/saildata/boat/harbor-14/",
                "goodoldboat.com",
                NQ,
                False,
                False,
                "404 not found",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "The manufacturer's current official site does not list this discontinued model (absence is not disconfirming) and no other qualifying source page was accessible within budget.",
    },
    "Q115815035": {  # Legende 1 Ton
        "searches": [
            '"Legende 1 Ton" voilier voile',
            'Jeanneau "Legende" One Ton class history archive',
        ],
        "evaluations": [
            _cite(
                "Q115815035-c1",
                "https://www.jeanneauowners.com/history/",
                "jeanneauowners.com",
                OWNERS_ASSOC,
                True,
                True,
                "Jeanneau Owners Network (7000+ members) history article: Doug Peterson developed the Sun Legende 41 in 1984; a special One Tonner race version 'Legend' in a modified mould/high-tech fibres was campaigned in 1980s/90s SORC and PHRF",
            ),
            _cite(
                "Q115815035-c2",
                "http://www.histoiredeshalfs.com/One%20Tonner/OP%2013%20Legende.htm",
                "histoiredeshalfs.com",
                SPECIALIST,
                False,
                False,
                "503 service unavailable",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Jeanneau Owners Network (owners' association) directly confirms the Legende/Sun Legende One Ton racing derivative as a Jeanneau production design family from 1984.",
    },
    "Q116909767": {  # Jeanneau Yachts 57
        "searches": ["Jeanneau Yachts 57 official specifications"],
        "evaluations": [
            _cite(
                "Q116909767-c1",
                "https://www.jeanneau.com/boats/sailboat/4-jeanneau-yachts/44-jeanneau-yachts-57",
                "jeanneau.com",
                MFG,
                True,
                True,
                "official Jeanneau product page for Jeanneau Yachts 57, designer Vittorio Garroni",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Official Jeanneau manufacturer page directly confirms the model.",
    },
    "Q117462175": {  # Lagoon 440
        "searches": [
            "Lagoon 440 catamaran official specifications",
            '"cata-lagoon.com" OR "catamaran-lagoon.com" Lagoon 440 official archive',
        ],
        "evaluations": [
            _cite(
                "Q117462175-c1",
                "https://www.multihulls-world.com/technical-specifications/lagoon-catamarans/lagoon-440",
                "multihulls-world.com",
                SPECIALIST,
                True,
                True,
                "Multihulls World (specialist multihull magazine, ~40yr test archive) confirms Lagoon 440 built by Lagoon Catamarans, designer VPLP",
                ["Q117462175-c2"],
            ),
            _cite(
                "Q117462175-c2",
                "https://www.katamarans.com/product-tag/lagoon/",
                "katamarans.com",
                SPECIALIST,
                True,
                True,
                "Katamarans.com (specialist catamaran documentation/history site) confirms Lagoon 440's panoramic-saloon/flybridge design",
                ["Q117462175-c1"],
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "two_independent_specialist_sources",
        "outcome_rationale": "Two independently-published specialist multihull documentation sources directly and consistently confirm the same model identity.",
    },
    "Q120535525": {  # Beneteau 34.7
        "searches": [
            "Beneteau 34.7 official specifications",
            '"First 34.7" class association Beneteau one-design',
        ],
        "evaluations": [
            _cite(
                "Q120535525-c1",
                "https://www.beneteau.com/first-2004-2006/first-347",
                "beneteau.com",
                MFG,
                True,
                True,
                "official Beneteau heritage page confirms First 34.7 (Beneteau 34.7), designer Bruce Farr, 2004-2016",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Official Beneteau manufacturer heritage page directly confirms the model.",
    },
    "Q114568600": {  # Espace 990
        "searches": ['"Espace 990" voilier Jeanneau OR Beneteau sailboat class'],
        "evaluations": [
            _cite(
                "Q114568600-c1",
                "https://www.jeanneau.com/en-us/boats/sailboat/36-autres-modeles-voile/562-espace-990",
                "jeanneau.com",
                MFG,
                True,
                True,
                "official Jeanneau page confirms Espace 990, designer Philippe Briand",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Official Jeanneau manufacturer page directly confirms the model.",
    },
    "Q113987990": {  # Newport 28-2
        "searches": [
            '"Newport 28-2" sailboat Capital Yachts',
            "Laguna Yachts owners association OR Newport sailboat association Capital Yachts",
        ],
        "evaluations": [
            _cite(
                "Q113987990-c1",
                "https://sailboat.guide/capital-yachts-info-class-association",
                "sailboat.guide",
                NQ,
                False,
                False,
                "page did not render content",
            ),
            _cite(
                "Q113987990-c2",
                "https://goodoldboat.com/saildata/boat/newport-28-ii/",
                "goodoldboat.com",
                SPECIALIST,
                True,
                True,
                "Good Old Boat saildata confirms Newport 28 Mk II built by Capital Yachts 1982-1987, designer C&C Design",
                [],
            ),
            _cite(
                "Q113987990-c3",
                "https://www.boat-specs.com/sailing/sailboats/capital-yachts/newport-28-mkii",
                "boat-specs.com",
                NQ,
                False,
                False,
                "page returned an error, no content",
            ),
            _cite(
                "Q113987990-c4",
                "https://en.wikipedia.org/wiki/Newport_28-2",
                "en.wikipedia.org",
                NQ,
                True,
                False,
                "discovery-only: cites sailboatdata.com, sailboat.guide, and a Practical Sailor review without live fetchable URLs",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "Only one accessible specialist source (Good Old Boat) was found; a second independent specialist (Practical Sailor) was identified only via discovery and the budget was exhausted before it could be evaluated.",
    },
    "Q114069597": {  # Newport 41S
        "searches": [
            '"Newport 41S" sailboat Capital Yachts',
            "Laguna Yachts owners association OR Newport sailboat association Capital Yachts",
        ],
        "evaluations": [
            _cite(
                "Q114069597-c1",
                "https://sailboat.guide/capital/newport-41s",
                "sailboat.guide",
                NQ,
                False,
                False,
                "page did not render content",
            ),
            _cite(
                "Q114069597-c2",
                "https://en.wikipedia.org/wiki/Newport_41S",
                "en.wikipedia.org",
                NQ,
                True,
                False,
                "discovery-only: cites sailboatdata.com, sailboat.guide, and a print book (Sherwood, Field Guide to Sailboats of North America); no accessible qualifying URL",
            ),
            _cite(
                "Q114069597-c3",
                "https://goodoldboat.com/saildata/boat/newport-41s/",
                "goodoldboat.com",
                NQ,
                False,
                False,
                "404 not found",
            ),
            _cite(
                "Q114069597-c4",
                "https://sailboat.guide/capital/newport-41s",
                "sailboat.guide",
                NQ,
                False,
                False,
                "retry, page did not render content",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "No qualifying source page was accessible within budget.",
    },
    "Q122144001": {  # Beneteau Cyclades 51.5
        "searches": [
            "Beneteau Cyclades 51.5 official specifications",
            "beneteau.com Cyclades 51.5 archive former sailboats",
        ],
        "evaluations": [
            _cite(
                "Q122144001-c1",
                "https://www.mauripro.com/collections/sailboat-data-beneteau-cyclades-515",
                "mauripro.com",
                NQ,
                True,
                False,
                "MauriPro Sailing is primarily a retail/e-commerce marketplace; sailboat data is a supplementary parts-finder tool, not qualifying specialist documentation",
            ),
            _cite(
                "Q122144001-c2",
                "https://www.beneteau.com/cyclades-2005-2010/cyclades-515",
                "beneteau.com",
                MFG,
                False,
                False,
                "404 not found",
            ),
            _cite(
                "Q122144001-c3",
                "https://sailboat.guide/beneteau/cyclades-515",
                "sailboat.guide",
                NQ,
                False,
                False,
                "page did not render content",
            ),
            _cite(
                "Q122144001-c4",
                "https://boatsector.com/specifications-cyclades-50-5-beneteau/",
                "boatsector.com",
                NQ,
                True,
                False,
                "wrong model (Cyclades 50.5, not 51.5); also a marketplace platform",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "No qualifying source page directly confirming this exact model was accessible within budget.",
    },
    "Q111947098": {  # Laguna 24S
        "searches": [
            '"Laguna 24" sailboat class manufacturer',
            "Laguna Yachts owners association OR Newport sailboat association Capital Yachts",
        ],
        "evaluations": [
            _cite(
                "Q111947098-c1",
                "https://goodoldboat.com/saildata/boat/laguna-24/",
                "goodoldboat.com",
                SPECIALIST,
                True,
                True,
                "Good Old Boat saildata confirms Laguna 24S/24T built by Laguna Yachts (California), designer W. Shad Turner, ~350 units",
            ),
            _cite(
                "Q111947098-c2",
                "https://sailboat.guide/laguna/24s",
                "sailboat.guide",
                NQ,
                False,
                False,
                "page did not render content",
            ),
            _cite(
                "Q111947098-c3",
                "https://www.boat-specs.com/sailing/sailboats/laguna/laguna-24s",
                "boat-specs.com",
                NQ,
                False,
                False,
                "page returned an error, no content",
            ),
            _cite(
                "Q111947098-c4",
                "https://en.wikipedia.org/wiki/Laguna_Yachts",
                "en.wikipedia.org",
                NQ,
                True,
                False,
                "discovery-only: cites sailboatdata.com and sailboat.guide (both excluded/inaccessible) and a print book",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "Only one accessible specialist source (Good Old Boat) was found; no second independent specialist or strong source was accessible within budget.",
    },
    "Q115805019": {  # RS21
        "searches": ["RS21 keelboat RS Sailing official"],
        "evaluations": [
            _cite(
                "Q115805019-c1",
                "https://www.rssailing.com/project/rs21/",
                "rssailing.com",
                MFG,
                True,
                True,
                "official RS Sailing page confirms RS21 one-design keelboat",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Official RS Sailing manufacturer page directly confirms the model.",
    },
    "Q114415084": {  # Sun Odyssey 32i
        "searches": ["Jeanneau Sun Odyssey 32i official jeanneau.com"],
        "evaluations": [
            _cite(
                "Q114415084-c1",
                "https://www.jeanneau.com/en-us/boats/sailboat/2-sun-odyssey/493-sun-odyssey-32i",
                "jeanneau.com",
                MFG,
                True,
                True,
                "official Jeanneau page confirms Sun Odyssey 32i, designer Philippe Briand",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Official Jeanneau manufacturer page directly confirms the model.",
    },
    "Q116007147": {  # Sun Fast 31
        "searches": ["Jeanneau Sun Fast 31 official jeanneau.com"],
        "evaluations": [
            _cite(
                "Q116007147-c1",
                "https://www.jeanneau.com/en-us/boats/sailboat/1-sun-fast/452-sun-fast-31",
                "jeanneau.com",
                MFG,
                True,
                True,
                "official Jeanneau page confirms Sun Fast 31 specifications",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Official Jeanneau manufacturer page directly confirms the model.",
    },
    "Q116814703": {  # Sun Odyssey 29.2
        "searches": ["Jeanneau Sun Odyssey 29.2 official jeanneau.com"],
        "evaluations": [
            _cite(
                "Q116814703-c1",
                "https://www.jeanneau.com/boats/sailboat/2-sun-odyssey/487-sun-odyssey-29-2",
                "jeanneau.com",
                MFG,
                True,
                True,
                "official Jeanneau page confirms Sun Odyssey 29.2, designer Jacques Fauroux",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Official Jeanneau manufacturer page directly confirms the model.",
    },
    "Q115813745": {  # Voyage 12.5
        "searches": ['"Voyage 12.5" catamaran Voyage Yachts official'],
        "evaluations": [
            _cite(
                "Q115813745-c1",
                "https://www.jeanneauowners.com/history/",
                "jeanneauowners.com",
                OWNERS_ASSOC,
                True,
                True,
                "Jeanneau Owners Network history confirms 'Voyage 1120 and 1250' passage-making designs by Guy Ribadeau Dumas alongside the Trinidad 48, in the 1980s Jeanneau ocean-cruiser portfolio",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Jeanneau Owners Network (owners' association) directly confirms the Voyage 1250/12.5 design as a Jeanneau production model.",
    },
    "Q116973712": {  # Jeanneau Yachts 60
        "searches": ["Jeanneau Yachts 60 official jeanneau.com"],
        "evaluations": [
            _cite(
                "Q116973712-c1",
                "https://www.jeanneau.com/boats/sailboat/4-jeanneau-yachts/653-jeanneau-yachts-60",
                "jeanneau.com",
                MFG,
                True,
                True,
                "official Jeanneau page confirms Jeanneau Yachts 60, designers Philippe Briand/Andrew Winch, first built 2021",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Official Jeanneau manufacturer page directly confirms the model.",
    },
    "Q122699417": {  # Nacra F16
        "searches": [
            "Nacra F16 catamaran official Nacra Sailing",
            "Nacra F16 class association official site",
        ],
        "evaluations": [
            _cite(
                "Q122699417-c1",
                "http://www.nacra.com.au/race/nacra-f16",
                "nacra.com.au",
                MFG,
                False,
                False,
                "certificate expired / could not connect",
            ),
            _cite(
                "Q122699417-c2",
                "https://www.sailing.org/classesandequipment/F16.php",
                "sailing.org",
                NQ,
                False,
                False,
                "404 not found",
            ),
            _cite(
                "Q122699417-c3",
                "https://www.ausnacra.com.au/international-classes/nacra-international",
                "ausnacra.com.au",
                CLASS_ASSOC,
                True,
                True,
                "Nacra Association of Australia (official national class association) confirms Formula 16 as a World-Sailing-linked multi-manufacturer beach-catamaran class and discusses Nacra's role/proprietary designs within it",
                ["Q122699417-c4"],
            ),
            _cite(
                "Q122699417-c4",
                "https://www.boat-specs.com/sailing/sailboats/nacra/nacra-f16",
                "boat-specs.com",
                SPECIALIST,
                True,
                True,
                "boat-specs.com confirms 'Nacra F16', builder Nacra, designer Morrelli & Melvin, built since 2012, still in production",
                ["Q122699417-c3"],
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Nacra Association of Australia (class association, a strong source class) directly documents the Formula 16 class family that Nacra actively builds under the 'Nacra F16' name, independently corroborated by boat-specs.com's product-level confirmation.",
    },
    "Q119855214": {  # Beneteau 1 Ton
        "searches": [
            'Beneteau "First 40.7" OR "Beneteau 1 Ton" 1990s One Ton Cup racer',
            'beneteau.com "1 Ton" first 40 evolution 1983 archive heritage',
        ],
        "evaluations": [
            _cite(
                "Q119855214-c1",
                "https://www.beneteau.com/en-us/first-1983-1985/first-40-evolution",
                "beneteau.com",
                MFG,
                False,
                False,
                "404 not found",
            ),
            _cite(
                "Q119855214-c2",
                "https://en.wikipedia.org/wiki/Beneteau_1_Ton",
                "en.wikipedia.org",
                NQ,
                False,
                False,
                "503 service unavailable",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "No qualifying source page was accessible within the 2-query budget. A promising Finot-Conq (designer) lead was found only via a third, over-budget query and was deliberately excluded from this determination as a self-corrected process deviation (see process_deviations).",
    },
    "Q19578127": {  # Trice (trimaran)
        "searches": [
            'Dick Newick "Trice" trimaran design history',
            '"dicknewickboats.com" Trice Acapella',
        ],
        "evaluations": [
            _cite(
                "Q19578127-c1",
                "http://dicknewickboats.com/",
                "dicknewickboats.com",
                DESIGNER,
                True,
                False,
                "official Dick Newick designer site lists many named designs (Tremolino, Cheers, Moxie, Val, etc.); 'Trice' is not among the names shown on this page",
            ),
            _cite(
                "Q19578127-c2",
                "http://www.dicknewickboats.com/tricia/",
                "dicknewickboats.com",
                DESIGNER,
                True,
                False,
                "page describes a distinct 36ft 1970 design named 'Tricia' (not 'Trice'); does not confirm 'Trice' as a separately listed design",
            ),
            _cite(
                "Q19578127-c3",
                "http://dicknewickboats.com/about/",
                "dicknewickboats.com",
                DESIGNER,
                True,
                False,
                "names only Moxie and Rogue Wave; mentions early-1960s St. Croix charter-trade trimarans without naming 'Trice' specifically",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "The designer's own official site does not clearly confirm a design named 'Trice' as distinct from the similarly-named 'Tricia'; this naming ambiguity could not be resolved within budget.",
    },
    "Q49142754": {  # Acapella (trimaran)
        "searches": [
            '"Acapella" trimaran Piver OR Newick OR Kelsall design history',
            '"Acapella" 31 foot trimaran Mike Birch designer builder',
        ],
        "evaluations": [
            _cite(
                "Q49142754-c1",
                "http://dicknewickboats.com/",
                "dicknewickboats.com",
                DESIGNER,
                True,
                False,
                "'Acapella' not listed among named Newick designs shown on this page",
            ),
            _cite(
                "Q49142754-c2",
                "https://greene-marine.com/about-maritime-history.htm",
                "greene-marine.com",
                MFG,
                True,
                True,
                "official Greene Marine page: 'Greene Marine began in 1978 with the building of Walter Greene's trimaran design Acapella'; raced 1978 Round Britain (1st in class) then sailed by Mike Birch (renamed Olympus Photo) to win the first Route du Rhum",
            ),
        ],
        "subject_outcome": "in_scope_identity",
        "evidence_strength": "strong_source",
        "outcome_rationale": "Greene Marine's own official history page (manufacturer/shipyard) directly and unambiguously identifies Acapella as Walter Greene's 1978 trimaran design.",
    },
    "Q19576865": {  # Amatasi 27
        "searches": [
            '"Amatasi 27" catamaran manufacturer',
            "Classic Boat magazine Amatasi Wharram design competition 2010 award",
        ],
        "evaluations": [
            _cite(
                "Q19576865-c1",
                "https://www.wharram.com/gallery/ethnic-designs/amatasi",
                "wharram.com",
                DESIGNER,
                False,
                False,
                "403 forbidden",
            ),
            _cite(
                "Q19576865-c2",
                "https://www.wharram.com/shop/study-plans/amatasi",
                "wharram.com",
                DESIGNER,
                False,
                False,
                "403 forbidden",
            ),
            _cite(
                "Q19576865-c3",
                "https://www.wharram.com/self-build-boats/ethnic-designs/",
                "wharram.com",
                DESIGNER,
                False,
                False,
                "403 forbidden",
            ),
            _cite(
                "Q19576865-c4",
                "https://proafile.com/multihull-boats/article/james-wharram-designs-win-design-competition-for-eco-fishing-boat",
                "proafile.com",
                SPECIALIST,
                True,
                True,
                "specialist multihull publication confirms James Wharram Designs' 27ft Amatasi double canoe won a 2010 Classic Boat magazine eco-fishing-boat design competition",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "The designer's own official site (wharram.com) consistently blocked access (403) across all attempted paths; only one specialist source was accessible, short of the two-independent-specialist bar.",
    },
    "Q21427576": {  # Ultim Armand Thiery / Macif
        "searches": ['"Macif" OR "Ultim Armand Thiery" trimaran VPLP design ocean racing'],
        "evaluations": [
            _cite(
                "Q21427576-c1",
                "https://www.vplp.fr/course/macif-100-actual-ultim-3/",
                "vplp.fr",
                DESIGNER,
                True,
                True,
                "official VPLP Design page documents one individual 2015-built Ultim-class trimaran commissioned for Francois Gabart, later transferred and renamed: Macif (2015-2021) -> Actual Ultim 3 (2021-2026) -> Armand Thiery (2026-present), tracking one hull's ownership/sponsor history, not a repeated production series",
            ),
        ],
        "subject_outcome": "out_of_scope",
        "evidence_strength": "strong_source",
        "outcome_rationale": "The naval-architecture firm's own page documents a single individual racing trimaran renamed across sponsor changes, matching the out-of-scope 'individual vessel/campaign' pattern rather than a reusable production model/class.",
    },
    "Q3548153": {  # vinta
        "searches": ["vinta Philippine outrigger boat museum National Museum Philippines"],
        "evaluations": [
            _cite(
                "Q3548153-c1",
                "https://philippinestudies.uk/mapping/items/show/27657",
                "philippinestudies.uk",
                MUSEUM,
                False,
                False,
                "403 forbidden",
            ),
            _cite(
                "Q3548153-c2",
                "https://guides.library.manoa.hawaii.edu/c.php?g=105238&p=685462",
                "guides.library.manoa.hawaii.edu",
                SPECIALIST,
                True,
                True,
                "University of Hawaii at Manoa Library maritime-heritage research guide states the vinta 'is a variant of the Visayan paraw... the difference is the type of sail rather than the hull', categorizing vinta as a traditional regional vessel-type category rather than a specific production model/class",
            ),
        ],
        "subject_outcome": "out_of_scope",
        "evidence_strength": "insufficient",
        "outcome_rationale": "An academic library maritime-heritage research guide confirms vinta is a generic traditional Philippine outrigger-boat type category, not a specific production sailboat model/class/design-family; treated conservatively as insufficient (a single specialist-tier source, not one of the seven strong classes) rather than strong_source.",
    },
    "Q22570174": {  # Gautier II
        "searches": [
            '"Gautier II" trimaran 1981 Atlantic crossing history',
            '"Gautier II" trimaran naufrage OR record traversee Atlantique 1981',
        ],
        "evaluations": [
            _cite(
                "Q22570174-c1",
                "https://timeline.museedelaplaisance.com/en/collection/racing-multihulls-trimarans-unstoppable-rise",
                "museedelaplaisance.com",
                MUSEUM,
                True,
                False,
                "French boating museum timeline page accessible but does not mention Gautier II specifically",
            ),
            _cite(
                "Q22570174-c2",
                "https://en.wikipedia.org/wiki/Gautier_II",
                "en.wikipedia.org",
                NQ,
                True,
                False,
                "discovery-only: single citation is a print book (Marchaj, Sail Performance, 2003) with no URL",
            ),
            _cite(
                "Q22570174-c3",
                "https://www.auxbulles.com/passion-bateaux-voile_record_traversee_atlantique_nord.html",
                "auxbulles.com",
                NQ,
                True,
                False,
                "general recreational water-sports site; does not mention Gautier II",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "No qualifying source page directly confirming Gautier II's identity was found or accessible within budget.",
    },
    "Q114353855": {  # Banaderos Express
        "searches": ['"Banaderos Express" ferry 2021 shipyard builder'],
        "evaluations": [
            _cite(
                "Q114353855-c1",
                "https://www.marinelink.com/news/austal-philippines-delivers-new-ferry-485643",
                "marinelink.com",
                SPECIALIST,
                True,
                True,
                "maritime trade publication confirms Banaderos Express (Austal Hull 395) is a 118m high-speed catamaran/trimaran vehicle-passenger ferry built by Austal Philippines for Fred. Olsen Express, launched 2021",
                [],
            ),
            _cite(
                "Q114353855-c2",
                "https://www.austal.com/vessels/banaderos-express",
                "austal.com",
                MFG,
                False,
                False,
                "404 not found",
            ),
            _cite(
                "Q114353855-c3",
                "https://www.marinelink.com/news/fred-olsens-new-ferry-completes-sea-490114",
                "marinelink.com",
                SPECIALIST,
                True,
                True,
                "same publisher (marinelink.com) as c1 -- NOT independent; confirms sea-trial completion, sister ship to Bajamar Express",
                [],
            ),
        ],
        "subject_outcome": "out_of_scope",
        "evidence_strength": "insufficient",
        "outcome_rationale": "A specialist maritime trade publication unambiguously confirms this is a passenger/vehicle ferry hull, not a sailboat; the only other accessible confirming citation is from the same publisher and is not independent, so evidence_strength is recorded as insufficient despite the clear out-of-scope subject matter.",
    },
    "Q104851951": {  # River-class ferry
        "searches": [
            '"River-class ferry" Sydney Transport NSW official',
            'Incat Crowther "River class" Sydney Ferries catamaran design',
        ],
        "evaluations": [
            _cite(
                "Q104851951-c1",
                "https://www.nsw.gov.au/media-releases/new-parramatta-river-class-ferry-arrives-sydney-ready-to-begin-service",
                "nsw.gov.au",
                NQ,
                True,
                False,
                "confirms the related but distinct 'Parramatta River Class' (generation 2, built by Richardson Devine Marine) -- not this exact QID's original 'River Class' (Incat Crowther design, 2020-2021)",
            ),
            _cite(
                "Q104851951-c2",
                "https://www.incatcrowther.com/vessels/river-class-ferry",
                "incatcrowther.com",
                DESIGNER,
                False,
                False,
                "404 not found",
            ),
            _cite(
                "Q104851951-c3",
                "https://www.transport.nsw.gov.au/news-and-events/media-releases/first-river-class-ferry-now-service",
                "transport.nsw.gov.au",
                NQ,
                False,
                False,
                "403 forbidden",
            ),
            _cite(
                "Q104851951-c4",
                "https://en.wikipedia.org/wiki/River-class_ferry",
                "en.wikipedia.org",
                NQ,
                True,
                False,
                "discovery-only: reference list (Transport for NSW, SMH, Canberra Times, Nine News, PS News) mostly archived/paywalled; no directly fetchable exact-match qualifying page found within budget",
            ),
        ],
        "subject_outcome": "unresolved",
        "evidence_strength": "insufficient",
        "outcome_rationale": "The exact 'River Class' (as distinct from the newer, related 'Parramatta River Class') could not be confirmed by an accessible qualifying source within budget.",
    },
    "Q4826103": {  # Auto Express 86 Class
        "searches": [
            '"Auto Express 86" ferry shipyard builder class',
            'Austal "Auto Express 86" class ferry official austal.com',
        ],
        "evaluations": [
            _cite(
                "Q4826103-c1",
                "https://www.austal.com/vessels/auto-express-86",
                "austal.com",
                MFG,
                False,
                False,
                "404 not found",
            ),
            _cite(
                "Q4826103-c2",
                "https://en.wikipedia.org/wiki/Auto_Express_86-class_ferry",
                "en.wikipedia.org",
                NQ,
                True,
                False,
                "discovery-only: citations are archive.org-mirrored Austal ASX announcement and Austal PDF spec sheet, not directly fetchable",
            ),
            _cite(
                "Q4826103-c3",
                "https://magazines.marinelink.com/Magazines/MaritimeReporter/200401/content/ferries-market-austal-208451",
                "marinelink.com",
                SPECIALIST,
                True,
                True,
                "Maritime Reporter & Engineering News (est. 1881, specialist maritime trade journal) confirms Austal built its 'seventh Auto Express 86 catamaran' for Canadian American Transportation Systems, operating Lake Ontario",
            ),
        ],
        "subject_outcome": "out_of_scope",
        "evidence_strength": "insufficient",
        "outcome_rationale": "A specialist maritime trade journal unambiguously confirms this is a class of high-speed catamaran ferries, not a sailboat; only one independent specialist source was accessible within budget.",
    },
    "Q30681833": {  # Emerald-class ferry
        "searches": [
            '"Emerald-class ferry" Washington State Ferries official',
            '"Emerald-class ferry" ship class builder',
        ],
        "evaluations": [
            _cite(
                "Q30681833-c1",
                "https://www.ship-technology.com/news/first-emerald-class-ferry-fairlight/",
                "ship-technology.com",
                SPECIALIST,
                True,
                True,
                "specialist maritime/shipping trade publication (GlobalData) confirms Emerald-class ferries built by Birdon for Sydney Ferries/Transdev, operating the Circular Quay-Manly route",
            ),
            _cite(
                "Q30681833-c2",
                "https://en.wikipedia.org/wiki/Emerald-class_ferry",
                "en.wikipedia.org",
                NQ,
                False,
                False,
                "503 service unavailable",
            ),
            _cite(
                "Q30681833-c3",
                "https://www.incat.com.au/vessels/emerald-class",
                "incat.com.au",
                MFG,
                False,
                False,
                "404 not found",
            ),
        ],
        "subject_outcome": "out_of_scope",
        "evidence_strength": "insufficient",
        "outcome_rationale": "A specialist maritime trade publication unambiguously confirms this is a passenger catamaran ferry class, not a sailboat; only one independent specialist source was accessible within the (self-corrected, see process_deviations) 2-query budget.",
    },
    "Q1129854": {  # USA 17
        "searches": ['"USA 17" BMW Oracle Racing trimaran America\'s Cup 2010'],
        "evaluations": [
            _cite(
                "Q1129854-c1",
                "https://www.vplp.fr/en/racing/usa17/",
                "vplp.fr",
                DESIGNER,
                True,
                True,
                "official VPLP Design page confirms USA 17 (BMW Oracle Racing 90) was a bespoke one-off trimaran commissioned by Russell Coutts specifically for the 2010 America's Cup, with no production-class/serial-variant mention",
            ),
        ],
        "subject_outcome": "out_of_scope",
        "evidence_strength": "strong_source",
        "outcome_rationale": "The naval-architecture firm's own official page directly confirms this was a bespoke one-off racing vessel, not a production class.",
    },
}

PROCESS_DEVIATIONS = [
    {
        "qid": "Q119855214",
        "description": (
            'A third discovery-search query (\'Groupe Finot "Beneteau" "1 Ton" OR "First 40 '
            "Evolution\" design portfolio') was issued before the 2-query-per-candidate cap was "
            "noticed. Its lead (a Finot-Conq designer-site redirect) was not fetched and is not "
            "relied upon in this candidate's retained determination, which uses only the first 2 "
            "queries and their resulting source-page evaluations."
        ),
    },
    {
        "qid": "Q30681833",
        "description": (
            "A third discovery-search query ('Birdon official site Emerald-class ferry Sydney') "
            "was issued before the 2-query-per-candidate cap was noticed. Its lead (Birdon's "
            "official site) was not fetched and is not relied upon in this candidate's retained "
            "determination, which uses only the first 2 queries and their resulting source-page "
            "evaluations."
        ),
    },
]


def _build_results(sample: Any) -> list[dict[str, Any]]:
    from hullq.bootstrap.wikimedia_sl0024_independent_verification import STRATUM_ORDER

    tag_by_qid: dict[str, str] = {}
    for tag in STRATUM_ORDER:
        for qid in sample.selected_by_stratum[tag]:
            tag_by_qid[qid] = tag

    results: list[dict[str, Any]] = []
    for qid in sample.selected_qids:
        log = RESEARCH_LOG[qid]
        searches = log["searches"]
        evaluations = log["evaluations"]
        combined = len(searches) + len(evaluations)
        results.append(
            {
                "qid": qid,
                "prior_tag": tag_by_qid[qid],
                "search_queries": searches,
                "search_query_count": len(searches),
                "evidence_citations": evaluations,
                "source_page_evaluation_count": len(evaluations),
                "combined_action_count": combined,
                "hit_budget_cap": combined >= 6,
                "subject_outcome": log["subject_outcome"],
                "evidence_strength": log["evidence_strength"],
                "outcome_rationale": log["outcome_rationale"],
            }
        )
    return results


# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------


def run_assemble() -> None:
    from hullq.bootstrap.wikimedia_sl0024_independent_verification import (
        build_candidate_metadata,
        build_verification_results_document,
        build_verification_sample_document,
        load_and_verify_immutable_boundaries,
        select_deterministic_sample,
    )

    boundaries = load_and_verify_immutable_boundaries()
    sample = select_deterministic_sample(list(boundaries.quality_review_rows))
    if set(sample.selected_qids) != set(RESEARCH_LOG):
        missing = set(sample.selected_qids) - set(RESEARCH_LOG)
        extra = set(RESEARCH_LOG) - set(sample.selected_qids)
        raise SystemExit(
            f"RESEARCH_LOG does not exactly cover the recomputed sample: missing={sorted(missing)} "
            f"extra={sorted(extra)}"
        )

    candidates = build_candidate_metadata(sample, boundaries)
    verification_sample = build_verification_sample_document(
        generated_at=GENERATED_AT, boundaries=boundaries, sample=sample, candidates=candidates
    )
    results = _build_results(sample)
    verification_results = build_verification_results_document(
        generated_at=GENERATED_AT,
        sample=sample,
        results=results,
        rights_access_ok=True,
        process_deviations=PROCESS_DEVIATIONS,
    )

    _validate_schema(
        verification_sample, VERIFICATION_SAMPLE_SCHEMA_PATH, label="verification_sample"
    )
    _validate_schema(
        verification_results, VERIFICATION_RESULTS_SCHEMA_PATH, label="verification_results"
    )

    SL0024_DIR.mkdir(parents=True, exist_ok=True)
    _write_json_lf(VERIFICATION_SAMPLE_PATH, verification_sample)
    _write_json_lf(VERIFICATION_RESULTS_PATH, verification_results)

    report = _build_report(verification_sample, verification_results)
    _write_text_lf(REPORT_PATH, report)

    digest_files = [
        "verification_sample.json",
        "verification_sample_schema.json",
        "verification_results.json",
        "verification_results_schema.json",
        "REPORT.md",
    ]
    digests = {}
    for name in digest_files:
        path = SL0024_DIR / name
        digests[name] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    artifact_digests = {
        "schema_version": "sl0024-artifact-digests-v1",
        "generated_at": GENERATED_AT,
        "excludes_self": "ARTIFACT-DIGESTS.json",
        "digests": digests,
    }
    _validate_schema(artifact_digests, ARTIFACT_DIGESTS_SCHEMA_PATH, label="artifact_digests")
    _write_json_lf(ARTIFACT_DIGESTS_PATH, artifact_digests)

    print(f"Wrote {VERIFICATION_SAMPLE_PATH}")
    print(f"Wrote {VERIFICATION_RESULTS_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {ARTIFACT_DIGESTS_PATH}")
    print(f"recommendation: {verification_results['recommendation']}")


def _build_report(verification_sample: dict[str, Any], verification_results: dict[str, Any]) -> str:
    m = verification_results["metrics"]
    lines = [
        "# HullQ SLICE-0024 Wikimedia Lead Independent Identity-Verification Pilot Report",
        "",
        f"**Generated at:** {verification_results['generated_at']}  ",
        "**Type:** DESIGN_RESEARCH -- research-only, no canonical/production mutation",
        "",
        "## Pinned SLICE-0023/0018 boundaries (reproduced before candidate selection)",
        "",
    ]
    for key, value in verification_sample["pinned_inputs"].items():
        lines.append(f"- `{key}`: {value}")
    lines += [
        "",
        "## Deterministic 18/6/6 sample",
        "",
        f"- stratum caps: {verification_sample['stratum_caps']}",
        f"- selected_count: **{verification_sample['selected_count']}**",
        "",
        "## Subject outcome totals",
        "",
    ]
    for outcome, count in m["subject_outcome_counts"].items():
        lines.append(f"- `{outcome}`: {count}")
    lines += [
        "",
        "## Evidence strength totals",
        "",
    ]
    for strength, count in m["evidence_strength_counts"].items():
        lines.append(f"- `{strength}`: {count}")
    lines += [
        "",
        "## Threshold set (24 prior plausible+ambiguous candidates)",
        "",
        f"- independently supported in_scope_identity: **{m['threshold_set_independently_supported_in_scope_count']}** (threshold >=12)",
        f"- strong_source in_scope_identity: **{m['threshold_set_strong_source_in_scope_count']}** (threshold >=8)",
        f"- median combined actions (independently supported): **{m['median_combined_actions_independently_supported_threshold_set']}** (ceiling <=4)",
        "",
        "## Research-action totals",
        "",
        f"- search_query_count_total: **{m['search_query_count_total']}** (ceiling {verification_results['research_boundary']['global_search_query_ceiling']})",
        f"- source_page_evaluation_count_total: **{m['source_page_evaluation_count_total']}** (ceiling {verification_results['research_boundary']['global_source_evaluation_ceiling']})",
        f"- combined_research_action_count_total: **{m['combined_research_action_count_total']}** (ceiling {verification_results['research_boundary']['global_combined_action_ceiling']})",
        f"- count hitting per-candidate budget cap: {m['count_hitting_per_candidate_budget_cap']}",
        f"- access-blocked source-page count: {m['access_blocked_source_page_count']}",
        f"- conflicts/unresolved count: {m['conflicts_and_unresolved_count']}",
        "",
        "## Source-class distribution",
        "",
    ]
    for cls, count in m["source_class_counts"].items():
        if count:
            lines.append(f"- `{cls}`: {count}")
    lines += [
        "",
        "## Recommendation (precommitted, mechanical rule)",
        "",
        f"- **{verification_results['recommendation']}**",
        "",
        "## Process deviations",
        "",
    ]
    if verification_results["process_deviations"]:
        for dev in verification_results["process_deviations"]:
            lines.append(f"- `{dev['qid']}`: {dev['description']}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Scope confirmation",
        "",
        "- No canonical HullQ Brand/Organization/BoatModel/BoatDesign row was created, modified or deleted.",
        "- No HullQ ID was minted for any candidate.",
        "- Wikipedia/Wikidata/SailboatData/search-result/generative-summary/forum/marketplace content was used only as discovery, never as qualifying verification evidence.",
        "- No newly evaluated external source was granted production/bulk/automation clearance.",
        "- Stage-3.3 enrichment was not started and SLICE-0025 was not created/started.",
        "",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def run_verify() -> None:
    from hullq.bootstrap.wikimedia_sl0024_independent_verification import (
        load_and_verify_immutable_boundaries,
        verify_artifact_digests_self_consistency,
        verify_metrics_self_consistency,
        verify_recommendation_self_consistency,
        verify_result_row_self_consistency,
        verify_sample_selection_self_consistency,
    )

    problems: list[str] = []

    boundaries = load_and_verify_immutable_boundaries()
    print("immutable boundaries: PASS", flush=True)

    verification_sample = json.loads(VERIFICATION_SAMPLE_PATH.read_bytes().decode("utf-8"))
    _validate_schema(
        verification_sample, VERIFICATION_SAMPLE_SCHEMA_PATH, label="verification_sample"
    )
    problems.extend(verify_sample_selection_self_consistency(verification_sample, boundaries))

    verification_results = json.loads(VERIFICATION_RESULTS_PATH.read_bytes().decode("utf-8"))
    _validate_schema(
        verification_results, VERIFICATION_RESULTS_SCHEMA_PATH, label="verification_results"
    )

    selected_set = set(verification_sample["selected_qids"])
    result_qids = [row["qid"] for row in verification_results["results"]]
    if set(result_qids) != selected_set or len(result_qids) != len(set(result_qids)):
        problems.append("results QID set does not exactly match verification_sample selected_qids")

    for row in verification_results["results"]:
        row_problems = verify_result_row_self_consistency(row)
        problems.extend(f"candidate {row['qid']}: {p}" for p in row_problems)

    problems.extend(verify_metrics_self_consistency(verification_results))
    problems.extend(verify_recommendation_self_consistency(verification_results))

    if verification_results["recommendation"] != "FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE":
        print(
            f"note: recommendation is {verification_results['recommendation']!r}, not the "
            "FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE this package was assembled with",
            flush=True,
        )

    artifact_digests = json.loads(ARTIFACT_DIGESTS_PATH.read_bytes().decode("utf-8"))
    _validate_schema(artifact_digests, ARTIFACT_DIGESTS_SCHEMA_PATH, label="artifact_digests")
    problems.extend(
        verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=SL0024_DIR
        )
    )

    if problems:
        print("VERIFICATION FAILED:", flush=True)
        for p in problems:
            print(f"  - {p}", flush=True)
        raise SystemExit(1)

    print("SLICE-0024 offline verification: PASS", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--assemble", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.assemble:
        run_assemble()
    elif args.verify:
        run_verify()


if __name__ == "__main__":
    main()
