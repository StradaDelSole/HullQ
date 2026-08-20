"""Deterministic benchmark bundle materializer — SLICE-0014.

Constructs ResearchEvidenceBundle objects for each of the 50 retained
SLICE-0011 benchmark cases from the committed manifest and retained wave
summary artifacts. No network access. No SailboatData field values.

All IDs and fingerprints are deterministic: same retained input + same code
produces the same bundle semantic fingerprints across repeated runs.

Synthetic benchmark scaffolding is explicitly distinguished from retained
research findings via:
  - source_id prefix 'hullq-benchmark-wave*-summary' (not a sailboat source);
  - observation notes stating BENCHMARK MATERIALIZATION;
  - bundle activity_id 'benchmark-0014-materialization'.

Usage:
    from scripts.benchmark.materializer import materialize_all, load_manifest
    bundles = materialize_all()   # {case_id: ResearchEvidenceBundle}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    ObservationApplicability,
    ProducerKind,
    ProducerMetadata,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    ReferenceCheckOutcome,
    ReferenceCrosscheck,
    ResearchEvidenceBundle,
    ResearchObservation,
    UnresolvedFinding,
    UnresolvedFindingSeverity,
)

MANIFEST_PATH = (
    Path(__file__).resolve().parents[2] / "research" / "benchmark" / "persistence" / "manifest.json"
)

BUNDLE_VERSION = "0014-v1"
ACTIVITY_ID = "benchmark-0014-materialization"
REFERENCE_SOURCE_ID = "sailboatdata-post-hoc-qa"

_PRODUCER = ProducerMetadata(
    kind=ProducerKind.DETERMINISTIC_TOOL,
    identifier="hullq-benchmark-materializer",
    version=BUNDLE_VERSION,
    model=None,
    prompt_or_rule_version=None,
)

_OBSERVED_AT = "2026-08-20T00:00:00Z"

_BENCHMARK_NOTE = (
    "BENCHMARK MATERIALIZATION: observation transcribed from retained SLICE-0011 "
    "wave summary artifact. Source is the wave summary document, not a primary "
    "sailboat source URL. Synthetic benchmark scaffolding for persistence path "
    "measurement only. Not canonical production evidence."
)

_FINDING_NOTE = (
    "BENCHMARK FINDING: conflict or unresolved question recorded from retained "
    "SLICE-0011 wave summary. Requires human review before canonical resolution."
)


class _CaseData(TypedDict):
    benchmark_problem: str
    reference_outcome: str
    conflict_finding: str | None


# ---------------------------------------------------------------------------
# Per-case retained findings (mechanically extracted from wave summaries)
# ---------------------------------------------------------------------------

_CASE_DATA: dict[str, _CaseData] = {
    "B01-001": {
        "benchmark_problem": (
            "Hallberg-Rassy 36 exposes explicit Mk I/Mk II generation boundaries "
            "with option-sensitive draft and displacement documented by the manufacturer; "
            "reference comparison does not preserve full generation and option semantics"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": (
            "Generation boundary timing and option-sensitive mass/draft configuration "
            "remain unresolved in retained evidence"
        ),
    },
    "B01-002": {
        "benchmark_problem": (
            "Westerly Centaur rudder evidence suggests a production-time change from "
            "skegless spade to skeg-supported form; generation/time-boundary timing "
            "remains unresolved pending documentary evidence"
        ),
        "reference_outcome": ReferenceCheckOutcome.CONFLICT,
        "conflict_finding": (
            "Rudder support evolution between original and later production runs remains "
            "unresolved; generation boundary timing requires documentary evidence not "
            "available in retained summary"
        ),
    },
    "B01-003": {
        "benchmark_problem": (
            "RM 1180 builder and specialist material expose combinatorial appendage options "
            "rather than a single keel/rudder pair; a flat configuration record loses real "
            "factory choices"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": None,
    },
    "B01-004": {
        "benchmark_problem": (
            "Najad 34 official multilingual PDF conflicts internally on production count; "
            "displacement remains intentionally unresolved pending stronger design-level "
            "evidence rather than using an individual-boat or reference value as fallback"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": (
            "Production count and displacement evidence conflict across internal multilingual "
            "sections of the primary source"
        ),
    },
    "B01-005": {
        "benchmark_problem": (
            "J/24 manufacturer nominal displacement and ORC measurement/rating displacement "
            "represent different measurement bases and must not be collapsed into a single "
            "scalar conflict"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B02-001": {
        "benchmark_problem": (
            "Dragonfly 32 has named-variant chronology that must not be flattened into one "
            "first_built value; reference comparison exposes definition/variant/identity issues "
            "rather than simple numeric disagreement"
        ),
        "reference_outcome": ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        "conflict_finding": (
            "Named-variant chronology transition events conflict across secondary sources"
        ),
    },
    "B02-002": {
        "benchmark_problem": (
            "OVNI 370 separates ballast from a separately stated keel weight and exposes "
            "centreboard up/down state as distinct evidence dimensions that must not be "
            "collapsed into one scalar"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B02-003": {
        "benchmark_problem": (
            "Garcia Exploration 45 explicitly has twin rudders each preceded by a protective "
            "skeg; the twin-rudder/skeg relationship is more specific than a single rudder-type "
            "label and requires relationship-aware representation"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B02-004": {
        "benchmark_problem": (
            "Boreal 44.2 has generation identity tied to named-variant chronology; reference "
            "comparison reveals partial model family coverage"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": None,
    },
    "B02-005": {
        "benchmark_problem": (
            "Island Packet 349 presents strong source agreement on principal dimensions; "
            "strong ordinary-field agreement in reference comparison with no material anomaly"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B02-006": {
        "benchmark_problem": (
            "Corsair 880 has well-documented generation/identity structure; reference "
            "comparison is broadly compatible with independent findings"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B02-007": {
        "benchmark_problem": (
            "Lagoon 42 commercial name was reused for a modern 2016 generation; appendage "
            "claims conflict across secondary/community sources and remain unresolved pending "
            "stronger authoritative evidence; reference comparison exposes "
            "definition/variant/identity issues"
        ),
        "reference_outcome": ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        "conflict_finding": (
            "Appendage configuration claims conflict across secondary and community sources "
            "with no single authoritative resolution available from retained evidence"
        ),
    },
    "B02-008": {
        "benchmark_problem": (
            "Nauticat 33/331 heritage material states the 331 received a new hull and deck "
            "in 1997 rather than being a simple string rename; identity determination requires "
            "explicit generation evidence rather than model-number proximity"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": None,
    },
    "B02-009": {
        "benchmark_problem": (
            "Catalina 316 explicitly labels both keel variant displacement values as Half Load; "
            "this measurement basis must survive normalization and must not be collapsed into "
            "a simple numeric conflict"
        ),
        "reference_outcome": ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        "conflict_finding": None,
    },
    "B02-010": {
        "benchmark_problem": (
            "Jeanneau Sun Odyssey 410 individual-hull mass values differ from the builder's "
            "explicit Lightship Displacement figure; evidence requires explicit scope/basis "
            "handling to avoid false generalization"
        ),
        "reference_outcome": ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        "conflict_finding": None,
    },
    "B02-011": {
        "benchmark_problem": (
            "CATANA Ocean Class exposes customizable geometry and daggerboard states; "
            "material multi-field disagreement across secondary and reference sources "
            "remains unresolved"
        ),
        "reference_outcome": ReferenceCheckOutcome.CONFLICT,
        "conflict_finding": (
            "Multi-field disagreement including daggerboard states, displacement and "
            "geometry remain unresolved across secondary sources"
        ),
    },
    "B02-012": {
        "benchmark_problem": (
            "Pogo 1 uses Light measurement trim as an explicit displacement basis label "
            "that must survive normalization as a distinct raw semantic label and must not "
            "be coerced into a standard basis"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B03-001": {
        "benchmark_problem": (
            "Hallberg-Rassy 42E suffix is identity-critical; orthogonal rig and keel "
            "configuration axes exist alongside individual-hull listings that must not "
            "silently redefine the design baseline; no reliable reference record located "
            "during benchmark pass"
        ),
        "reference_outcome": ReferenceCheckOutcome.NO_REFERENCE_RECORD_FOUND,
        "conflict_finding": None,
    },
    "B03-002": {
        "benchmark_problem": (
            "BENETEAU Oceanis 37 primary authoritative page is incomplete; individual-hull "
            "versus design-level mass semantics require explicit basis/scope handling; "
            "configuration/basis coverage differs in reference comparison"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": (
            "Configuration/basis coverage gap and individual-hull versus design-level "
            "mass discrepancy remain unresolved"
        ),
    },
    "B03-003": {
        "benchmark_problem": (
            "Rustler 36 highly authoritative appendage taxonomy from builder material must "
            "remain a separate evidence class from hull-specific numeric evidence; reference "
            "taxonomy is less compatible with the builder's explicit keel-hung statement"
        ),
        "reference_outcome": ReferenceCheckOutcome.CONFLICT,
        "conflict_finding": (
            "Reference taxonomy conflict with builder's explicit keel-hung statement"
        ),
    },
    "B03-004": {
        "benchmark_problem": (
            "Seafarer 26 (McCurdy and Rhodes) built 1977-1985 with explicit partial-skeg "
            "rudder support; an earlier different Seafarer 26 was designed by Philip Rhodes; "
            "model name reuse requires generation disambiguation from secondary sources"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B03-005": {
        "benchmark_problem": (
            "Southerly 110 swing keel state, fixed grounding structure, twin-rudder count "
            "and protective-skeg relationship are separate facts; mass differences among "
            "hull-specific and secondary records require explicit scope/basis review"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": (
            "Mass/ballast differences among hull-specific and secondary records remain "
            "unresolved pending basis/scope determination"
        ),
    },
    "B03-006": {
        "benchmark_problem": (
            "Contessa 32 is a live new-build lineage; current-new-build values versus "
            "historical design values need explicit era/applicability semantics to prevent "
            "inappropriate merging across production eras"
        ),
        "reference_outcome": ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        "conflict_finding": None,
    },
    "B03-007": {
        "benchmark_problem": (
            "AMEL Super Maramu 2000 official history explicitly distinguishes it from the "
            "preceding Super Maramu with an explicit production chronology; reference "
            "chronology conflicts with builder history"
        ),
        "reference_outcome": ReferenceCheckOutcome.CONFLICT,
        "conflict_finding": (
            "Chronology of Super Maramu versus Super Maramu 2000 production conflicts "
            "between builder history and reference chronology"
        ),
    },
    "B03-008": {
        "benchmark_problem": (
            "Moody 33 Mk I and Mk II apparent sail-area conflict can actually be a "
            "measurement-definition conflict; Mk II changes concentrate on "
            "accommodation/cockpit rather than a new underwater design"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B04-001": {
        "benchmark_problem": (
            "Sadler 34 factory option space includes deep fin, shallow fin, bilge/twin-keel "
            "and centreboards inside shallow fins; SE suffix reflects equipment/fitout upgrade "
            "rather than a new hull design"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": None,
    },
    "B04-002": {
        "benchmark_problem": (
            "Albin Vega class-association material distinguishes design/prototype/production "
            "chronology; rudder attachment to aft keel region requires richer taxonomy than "
            "a flat keel label; reference chronology/draft differences remain research questions"
        ),
        "reference_outcome": ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        "conflict_finding": (
            "Chronology event semantics and draft differences remain unresolved across "
            "class-association and secondary sources"
        ),
    },
    "B04-003": {
        "benchmark_problem": (
            "Hallberg-Rassy 35 Rasmus post-hoc comparison reveals competing reference "
            "identities around Rasmus 35 and Hallberg-Rassy 35; string similarity is "
            "insufficient to select one canonical identity"
        ),
        "reference_outcome": ReferenceCheckOutcome.IDENTITY_DISAMBIGUATION_REQUIRED,
        "conflict_finding": (
            "Competing reference identities around Rasmus 35 and Hallberg-Rassy 35 "
            "cannot be resolved from retained string similarity alone"
        ),
    },
    "B04-004": {
        "benchmark_problem": (
            "Vancouver 27 has weak-primary-source/changed-builder reconstruction challenge "
            "plus nearby successor identity contamination risk from the later modified "
            "Vancouver 28 design"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B04-005": {
        "benchmark_problem": (
            "F-27/Corsair F-27 sailing/folded geometry state, board state and historical "
            "naming must coexist without duplicate identity or a single hidden displacement "
            "scalar; some mass drift across publications"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": (
            "Mass drift across publications and board-state interaction with displacement "
            "remain unresolved"
        ),
    },
    "B04-006": {
        "benchmark_problem": (
            "Prout Snowgoose 37 Elite is materially wider and evolved, not a harmless "
            "marketing suffix; late individual-hull records labelled simply Snowgoose 37 "
            "can be physically closer to the Elite family than the original baseline"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": (
            "Model/evolution identity must be resolved before projecting a late individual "
            "hull onto the original baseline"
        ),
    },
    "B04-007": {
        "benchmark_problem": (
            "Westerly Konsort fin/twin/lifting keel variants have configuration-specific "
            "draft and ballast; production count and displacement conflict among reputable "
            "sources needs review rather than forced resolution"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": (
            "Production count and displacement conflict among reputable sources cannot "
            "be resolved from retained evidence"
        ),
    },
    "B04-008": {
        "benchmark_problem": (
            "Heavenly Twins 26/New 27 Mk labels have unequal technical significance; "
            "Mk2A introduced a new hull mould and longer keels while Mk3 retained that "
            "hull but changed deck and interior geometry"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B05-001": {
        "benchmark_problem": (
            "MacGregor 26 family D/S/X/M variants have materially different hull/use/board/"
            "rudder/rig semantics; suffix syntax alone cannot decide the lineage relationship; "
            "shared branding and trailerability do not imply one BoatDesign"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": (
            "Independent sources give slightly different transition-year chronologies "
            "for the D/S to X/M family transition"
        ),
    },
    "B05-002": {
        "benchmark_problem": (
            "BENETEAU First 35 commercial string recurs across decades and different naval "
            "architects; Carbon Edition is more plausibly a variant inside the later Farr "
            "generation than an unrelated hull"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": None,
    },
    "B05-003": {
        "benchmark_problem": (
            "Moody 36 archive explicitly separates earlier and later families designed by "
            "different naval architects; S/DS suffixes can be derivatives of one underlying "
            "hull family requiring evidence-driven split decisions"
        ),
        "reference_outcome": ReferenceCheckOutcome.PARTIAL_MATCH,
        "conflict_finding": None,
    },
    "B05-004": {
        "benchmark_problem": (
            "Hallberg-Rassy 352 HR Club catalogue contains malformed mass-unit presentation "
            "which must be preserved and flagged rather than blindly parsed; strong source "
            "authority does not guarantee syntactically valid observations"
        ),
        "reference_outcome": ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        "conflict_finding": (
            "Malformed mass-unit presentation in the primary catalogue source requires "
            "specific technical expertise to interpret correctly"
        ),
    },
    "B05-005": {
        "benchmark_problem": (
            "Swan 36 original S&S design and modern ClubSwan 36 by Juan Kouyoumdjian "
            "are radically different boats; Nautor connects them as brand heritage not "
            "technical identity; production-count conflict exists for the original model"
        ),
        "reference_outcome": ReferenceCheckOutcome.CONFLICT,
        "conflict_finding": (
            "Production-count conflict for the original Swan 36 exists across otherwise "
            "reputable sources"
        ),
    },
    "B05-006": {
        "benchmark_problem": (
            "Catalina 36 Mk II does not represent a wholly new underwater hull; the Mk "
            "transition concentrated on stern/cockpit/deck/interior; generation relationship "
            "must be evidence-driven rather than assumed from suffix syntax"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B05-007": {
        "benchmark_problem": (
            "Dehler 34 name recurs across three generations from different eras designed by "
            "different architects; builder marketing heritage connects them but each generation "
            "has its own hull dimensions"
        ),
        "reference_outcome": ReferenceCheckOutcome.IDENTITY_DISAMBIGUATION_REQUIRED,
        "conflict_finding": None,
    },
    "B05-008": {
        "benchmark_problem": (
            "Hunter 37 Legend identity is critical context not decorative text; Hunter 37 "
            "alone is ambiguous between the original Cherubini design and later Legend-era "
            "designs described by owners as radically different boats"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B06-001": {
        "benchmark_problem": (
            "C&C 35 Mk II carried real hull/appendage/weight/sail-plan consequences from a "
            "1973 redesign, unlike Catalina 36 Mk II or HR 312; suffix syntax cannot "
            "determine generation semantics by itself"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B06-002": {
        "benchmark_problem": (
            "Hallberg-Rassy 312 Mk II changes focus on superstructure/cockpit/interior/"
            "headroom while hull and rig remain the same; HR Club shows systematic malformed "
            "mass-unit rendering that repeats across the source family"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": (
            "Malformed mass-unit rendering repeats in the authoritative source family, "
            "requiring expert review to interpret correctly"
        ),
    },
    "B06-003": {
        "benchmark_problem": (
            "ETAP 32s standard and tandem-keel configurations have different draft, "
            "displacement and keel weight together in one factory option; manual also "
            "distinguishes net versus fully-loaded mass basis as a separate dimension"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B06-004": {
        "benchmark_problem": (
            "Pearson 35 archive explicitly warns that measurements apply to a documented "
            "model year and may not represent the full production run; board state and "
            "multiple mass/calculation semantics coexist inside one commercial design identity"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B06-005": {
        "benchmark_problem": (
            "Ericson 35 same builder/model number was reused across technically distinct "
            "designs (CCA long-keel, Bruce King fin/spade, later replacement); lineage "
            "relation between generations can itself remain uncertain evidence"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": (
            "Lineage relation between successive Ericson 35 generations can itself remain "
            "uncertain evidence despite strong structural confirmation of separate identities"
        ),
    },
    "B06-006": {
        "benchmark_problem": (
            "Bristol 35.5 suffix C encodes centerboard configuration rather than proving "
            "a wholly unrelated hull; centerboard control mechanics are documented "
            "independently showing suffix-as-configuration rather than suffix-as-generation"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B06-007": {
        "benchmark_problem": (
            "Gemini 105Mc owner's manual states one centerboard is installed per hull but "
            "legitimate sailing procedures include 0, 1 or 2 boards deployed; installed "
            "appendage count and deployed operating-state count are different concepts"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B06-008": {
        "benchmark_problem": (
            "J/105 class association rules encode compliance limits, permitted variation and "
            "measurement procedures rather than automatically nominal production values; "
            "class-rule constraint is not the same claim type as a nominal builder specification"
        ),
        "reference_outcome": ReferenceCheckOutcome.MATCH,
        "conflict_finding": None,
    },
    "B06-009": {
        "benchmark_problem": (
            "Bavaria 38 owner's manual exposes normal-keel versus lead-keel configurations "
            "with different draft, ballast and ready-for-sailing mass; neighboring commercial "
            "identities including Ocean 38, 38 Cruiser and Match 38 create identity "
            "disambiguation risk"
        ),
        "reference_outcome": ReferenceCheckOutcome.IDENTITY_DISAMBIGUATION_REQUIRED,
        "conflict_finding": None,
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unbounded_applicability() -> ObservationApplicability:
    return ObservationApplicability(
        first_year=None,
        last_year=None,
        hull_number_from=None,
        hull_number_to=None,
        market_or_region=None,
        named_variant_hint=None,
        design_option_hints=None,
        operating_state_hint=None,
        individual_hull_or_listing_ref=None,
        unknown_or_unbounded=True,
    )


def _obs_id(case_id: str, n: int) -> str:
    return f"benchmark-{case_id.lower()}-obs-{n:02d}"


def _finding_id(case_id: str, n: int) -> str:
    return f"benchmark-{case_id.lower()}-finding-{n:02d}"


def _crosscheck_id(case_id: str, n: int) -> str:
    return f"benchmark-{case_id.lower()}-cc-{n:02d}"


def _bundle_id(case_id: str) -> str:
    return f"hullq-benchmark-{case_id.lower()}"


def _source_id(wave: int) -> str:
    return f"hullq-benchmark-wave{wave:02d}-summary"


def _make_observation(
    case_id: str,
    n: int,
    wave: int,
    research_target: ResearchTarget,
    text: str,
    evidence_type: EvidenceType,
    claim_semantics: ClaimSemantics,
) -> ResearchObservation:
    return ResearchObservation(
        observation_id=_obs_id(case_id, n),
        research_target=research_target,
        source_id=_source_id(wave),
        source_locator=SourceLocator(
            page=None,
            section=None,
            anchor=None,
            table=None,
            figure=None,
            record_key=case_id,
        ),
        raw=RawObservation(
            kind=RawObservationKind.TEXT_FRAGMENT,
            value=text,
            unit=None,
            excerpt=text[:100],
        ),
        normalized_candidate=None,
        evidence_type=evidence_type,
        claim_semantics=claim_semantics,
        applicability=_unbounded_applicability(),
        producer=_PRODUCER,
        research_context=ResearchContext(
            research_job_id=None,
            activity_id=ACTIVITY_ID,
        ),
        observed_at=_OBSERVED_AT,
        confidence=ConfidenceLevel.MEDIUM,
        supersedes_observation_id=None,
        intended_subject_kind_hint=None,
        intended_field_pointer=None,
        notes=_BENCHMARK_NOTE,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_manifest() -> dict[str, Any]:
    """Load and return the benchmark manifest JSON dict."""
    result: dict[str, Any] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return result


def materialize_bundle(case: dict[str, Any]) -> ResearchEvidenceBundle:
    """Construct a deterministic ResearchEvidenceBundle from one manifest case.

    All IDs are deterministic from case_id. The source_id uses the benchmark
    wave summary document identifier (not a sailboat production source). No
    SailboatData field values are introduced. No network access occurs.

    The bundle is pre-canonical: no canonical ProvenanceSubject is created or
    implied. promoted_evidence is always empty.
    """
    case_id: str = case["benchmark_case_id"]
    wave: int = int(case["wave"])
    manufacturer: str | None = case.get("manufacturer") or None
    model: str = str(case["model"])

    research_target = ResearchTarget(
        manufacturer=manufacturer,
        model=model,
        first_built=None,
    )

    data = _CASE_DATA[case_id]
    benchmark_problem: str = data["benchmark_problem"]
    reference_outcome_str: str = data["reference_outcome"]
    conflict_finding_text: str | None = data["conflict_finding"]
    classification: dict[str, int] = case["classification"]

    # Determine primary evidence_type and claim_semantics from classification flags.
    # identity_lineage=1 → identity_or_chronology_claim; config_state=1 → operating_state;
    # else → other
    if classification.get("identity_lineage", 0):
        claim_sem = ClaimSemantics.IDENTITY_OR_CHRONOLOGY_CLAIM
    elif classification.get("config_state", 0):
        claim_sem = ClaimSemantics.OPERATING_STATE_VALUE
    elif classification.get("basis_definition", 0):
        claim_sem = ClaimSemantics.PUBLISHED_CALCULATION
    else:
        claim_sem = ClaimSemantics.OTHER

    ev_type = (
        EvidenceType.MANUFACTURER_SPECIFICATION
        if classification.get("authoritative_path", 0)
        else EvidenceType.NARRATIVE_TEXT
    )

    # Primary observation: retained benchmark problem finding.
    primary_obs = _make_observation(
        case_id=case_id,
        n=1,
        wave=wave,
        research_target=research_target,
        text=benchmark_problem,
        evidence_type=ev_type,
        claim_semantics=claim_sem,
    )

    observations: list[ResearchObservation] = [primary_obs]

    # Unresolved finding (only for conflict_unresolved=1 cases).
    findings: list[UnresolvedFinding] = []
    if conflict_finding_text is not None:
        findings.append(
            UnresolvedFinding(
                finding_id=_finding_id(case_id, 1),
                topic="conflict_or_unresolved_evidence",
                description=conflict_finding_text,
                related_observation_ids=frozenset({_obs_id(case_id, 1)}),
                severity=UnresolvedFindingSeverity.REVIEW,
            )
        )

    # Reference crosscheck — outcome-only, no reference field values stored.
    crosschecks: list[ReferenceCrosscheck] = [
        ReferenceCrosscheck(
            crosscheck_id=_crosscheck_id(case_id, 1),
            reference_source_id=REFERENCE_SOURCE_ID,
            topic_or_field=None,
            outcome=ReferenceCheckOutcome(reference_outcome_str),
            notes=(
                "Post-hoc reference comparison outcome only. No reference field values "
                "are stored. See retained wave summary for crosscheck rationale."
            ),
        )
    ]

    return ResearchEvidenceBundle(
        bundle_id=_bundle_id(case_id),
        bundle_version=BUNDLE_VERSION,
        research_target=research_target,
        research_job_id=None,
        activity_id=ACTIVITY_ID,
        observations=tuple(observations),
        unresolved_findings=tuple(findings),
        promoted_evidence=(),
        reference_crosschecks=tuple(crosschecks),
    )


def materialize_all() -> dict[str, ResearchEvidenceBundle]:
    """Materialize bundles for all 50 benchmark cases.

    Returns a dict mapping benchmark_case_id → ResearchEvidenceBundle.
    Always deterministic: same retained input + same code produces the same
    bundle semantic fingerprints.
    """
    manifest = load_manifest()
    result: dict[str, ResearchEvidenceBundle] = {}
    for case in manifest["cases"]:
        case_id = str(case["benchmark_case_id"])
        result[case_id] = materialize_bundle(case)
    return result
