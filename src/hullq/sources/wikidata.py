"""Wikidata CC0 rights-gated adapter — SLICE-0008.

First controlled real external acquisition adapter. Implements:
  - bounded adapter configuration
  - SLICE-0007 automated-ingestion rights gate before any HTTP request
  - sailboat-class SPARQL discovery probe (Q106179098)
  - entity acquisition via official wbgetentities API
  - qualifier-aware field extraction for common scalar properties
  - SLICE-0006 FieldEvidence production with preserved raw observations
  - SLICE-0004 unit normalization reused for supported quantity units
  - reproducible quality/coverage report

Does not implement: canonical FieldResolution, BoatModel/BoatDesign writes,
keel/rudder/skeg taxonomy, persistence, broad ingestion, or fuzzy identity
resolution.

Core rule: the SLICE-0007 automated-ingestion rights gate must be checked and
return ALLOWED before any HTTP request is dispatched. The gate outcome drives
all subsequent behavior; the adapter never grants itself permission from a URL,
license name, or payload content.
"""

from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from hullq.domain.measurements import (
    LengthUnit,
    MassUnit,
    MeasurementObservation,
    Quantity,
    Unit,
    normalize_measurement,
)
from hullq.domain.provenance import (
    ConfidenceLevel,
    EvidenceType,
    FieldEvidence,
    JsonPointer,
    NormalizedCandidate,
    ProducerKind,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
    SubjectKind,
)
from hullq.sources.rights import (
    DecisionOutcome,
    SourceUsageMetrics,
    SourceUse,
    SourceUseDecision,
    check_source_use,
)

__all__ = [
    "BOOTSTRAP_ENTITY_API_ENDPOINT",
    "BOOTSTRAP_ENTITY_API_VERSION",
    "BOOTSTRAP_SPARQL_ENDPOINT",
    "BOOTSTRAP_SPARQL_QUERY_VERSION",
    "SLICE_0008_ITEM_CEILING",
    "WIKIDATA_BOOTSTRAP_SAFETY_CEILING",
    "WIKIDATA_SOURCE_ID",
    "WikidataAcquisitionError",
    "WikidataAdapter",
    "WikidataAdapterConfig",
    "WikidataEntityData",
    "WikidataHTTPError",
    "WikidataMalformedResponse",
    "WikidataProbeResult",
    "WikidataQualityReport",
    "WikidataRightsBlocked",
    "WikidataThrottled",
    "WikidataTimeout",
    "validate_qid",
]

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

WIKIDATA_SOURCE_ID = "SRC_WIKIDATA_API_2026"

# SLICE-0008 operational cap — documented here, not a rights/licence rule.
# This is a bounded-probe ceiling specific to the controlled SLICE-0008 scope.
SLICE_0008_ITEM_CEILING = 100

# SLICE-0017 broad-bootstrap hard safety ceiling — independent of and does not
# mutate SLICE_0008_ITEM_CEILING or WikidataAdapterConfig.item_limit, which
# retain their original SLICE-0008 controlled-probe meaning unchanged. The
# bootstrap requested candidate limit (1,000) is a runner-level policy choice
# defined in hullq.bootstrap.wikidata_tier0; this ceiling (1,500) is the
# adapter-level hard upper bound below which the bootstrap-specific discovery
# and acquisition methods on WikidataAdapter operate.
WIKIDATA_BOOTSTRAP_SAFETY_CEILING = 1500

# ---------------------------------------------------------------------------
# Internal API constants
# ---------------------------------------------------------------------------

_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
_ENTITY_API_ENDPOINT = "https://www.wikidata.org/w/api.php"

# Documented wbgetentities batch limit.
_ENTITY_API_BATCH_SIZE = 50

# Wikidata sailboat class QID (instance of sailboat class).
_SAILBOAT_CLASS_QID = "Q106179098"

# Deterministic SPARQL probe — versioned so changes are auditable.
_SPARQL_QUERY_VERSION = "SLICE-0008-v1"

# SLICE-0017 bootstrap discovery query version — distinct from the SLICE-0008
# controlled-probe query version above; the bootstrap query additionally
# orders results deterministically before LIMIT.
_SPARQL_QUERY_VERSION_BOOTSTRAP = "SLICE-0017-bootstrap-v1"

# Public audit-facing aliases of the bootstrap acquisition path identity/version,
# retained verbatim in the SLICE-0017 bootstrap manifest for reproducibility
# (docs/slices/SLICE-0017-*.md "manifest + report audit completeness").
BOOTSTRAP_SPARQL_QUERY_VERSION = _SPARQL_QUERY_VERSION_BOOTSTRAP
BOOTSTRAP_SPARQL_ENDPOINT = _SPARQL_ENDPOINT
BOOTSTRAP_ENTITY_API_ENDPOINT = _ENTITY_API_ENDPOINT
# Documents the exact wbgetentities request shape used for bootstrap entity
# acquisition (action=wbgetentities, props=labels|aliases|claims, batches of
# _ENTITY_API_BATCH_SIZE); versioned so a future change to the request shape
# is auditable from retained manifests alone.
BOOTSTRAP_ENTITY_API_VERSION = "wbgetentities-labels-aliases-claims-v1"


def _build_sparql_query(limit: int) -> str:
    """Build the deterministic SPARQL discovery query for sailboat-class items.

    Uses a versioned header so probe queries are auditable and reproducible.
    The LIMIT is set by the caller, not hardcoded in the query body.
    """
    return (
        f"# HullQ Wikidata SPARQL discovery probe {_SPARQL_QUERY_VERSION}\n"
        f"SELECT ?item WHERE {{\n"
        f"  ?item wdt:P31 wd:{_SAILBOAT_CLASS_QID} .\n"
        f"}} LIMIT {limit}\n"
    )


def _build_bootstrap_sparql_query(limit: int) -> str:
    """Build the deterministic ordered SPARQL discovery query for the
    SLICE-0017 broad Tier-0 bootstrap.

    Unlike ``_build_sparql_query`` (the SLICE-0008 controlled-probe query,
    left unchanged), this query adds an explicit stable ``ORDER BY ?item``
    before ``LIMIT`` so that repeated runs return the same first-N candidates
    in the same deterministic order, per the SLICE-0017 candidate-set
    boundary contract.
    """
    return (
        f"# HullQ Wikidata SPARQL bootstrap discovery {_SPARQL_QUERY_VERSION_BOOTSTRAP}\n"
        f"SELECT ?item WHERE {{\n"
        f"  ?item wdt:P31 wd:{_SAILBOAT_CLASS_QID} .\n"
        f"}} ORDER BY ?item LIMIT {limit}\n"
    )


# ---------------------------------------------------------------------------
# Wikidata property identifiers
# ---------------------------------------------------------------------------

_PROP_MANUFACTURER = "P176"
_PROP_DESIGNER = "P287"
_PROP_LENGTH = "P2043"
_PROP_WIDTH = "P2049"
_PROP_HEIGHT = "P2048"
_PROP_MASS = "P2067"
_PROP_TOTAL_PRODUCED = "P1092"

# Qualifier property used to distinguish concept variants (e.g., LOA vs LWL).
_QUALIFIER_OF = "P642"

# QIDs of the qualifier value entities (values of the P642 "of" qualifier).
_QUAL_LOA = "Q2358152"  # length overall
_QUAL_LWL = "Q1817392"  # length at waterline
_QUAL_DRAFT = "Q244777"  # draft
_QUAL_DISPLACEMENT = "Q5636358"  # displacement
_QUAL_BALLAST = "Q5461048"  # ballast

# ---------------------------------------------------------------------------
# Wikidata unit QID → (Quantity, Unit) mapping
# Only confirmed, common unit QIDs. Unknown units produce no normalized
# candidate; raw quantity/unit are always preserved separately.
# ---------------------------------------------------------------------------

_UNIT_QID_MAP: dict[str, tuple[Quantity, Unit]] = {
    "Q11573": (Quantity.LENGTH, LengthUnit.METRE),
    "Q174728": (Quantity.LENGTH, LengthUnit.CENTIMETRE),
    "Q3710": (Quantity.LENGTH, LengthUnit.FOOT),
    "Q218593": (Quantity.LENGTH, LengthUnit.INCH),
    "Q11570": (Quantity.MASS, MassUnit.KILOGRAM),
    "Q12152": (Quantity.MASS, MassUnit.GRAM),
    "Q11369": (Quantity.MASS, MassUnit.METRIC_TONNE),
    "Q37795": (Quantity.MASS, MassUnit.POUND),
}

# ---------------------------------------------------------------------------
# Field pointers (paths into BOAT_DESIGN_SCHEMA.v0.5 for evidence subjects)
# ---------------------------------------------------------------------------

_PTR_LOA = JsonPointer("/baseline/dimensions/loa_m")
_PTR_LWL = JsonPointer("/baseline/dimensions/lwl_m")
_PTR_BEAM = JsonPointer("/baseline/dimensions/beam_m")
_PTR_DRAFT = JsonPointer("/baseline/dimensions/draft_min_m")
_PTR_DISPLACEMENT = JsonPointer("/baseline/dimensions/displacement_kg")
_PTR_BALLAST = JsonPointer("/baseline/dimensions/ballast_kg")
_PTR_BUILDERS = JsonPointer("/relationships/builders")
_PTR_DESIGNERS = JsonPointer("/relationships/designers")
_PTR_NUMBER_BUILT = JsonPointer("/relationships/number_built")

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_QID_RE = re.compile(r"^Q[1-9][0-9]*$")
_ENTITY_URI_RE = re.compile(r"https?://www\.wikidata\.org/entity/(Q[1-9][0-9]*)$")
_UNIT_URI_RE = re.compile(r"https?://www\.wikidata\.org/entity/(Q[1-9][0-9]*)$")

# ---------------------------------------------------------------------------
# Shared producer metadata for all evidence produced by this adapter
# ---------------------------------------------------------------------------

_ADAPTER_PRODUCER = ProducerMetadata(
    kind=ProducerKind.DETERMINISTIC_TOOL,
    identifier="hullq-wikidata-adapter",
    version=_SPARQL_QUERY_VERSION,
    model=None,
    prompt_or_rule_version=None,
)

# ---------------------------------------------------------------------------
# Public configuration value-object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WikidataAdapterConfig:
    """Immutable configuration for a single controlled Wikidata probe.

    ``user_agent`` must be a descriptive string identifying HullQ and providing
    a contact identifier, per Wikimedia User-Agent policy.
    ``item_limit`` bounds the number of items fetched in this probe; it must be
    within [1, SLICE_0008_ITEM_CEILING]. This is a SLICE-0008 operational cap,
    not a rights or licence rule.
    """

    user_agent: str
    request_timeout_seconds: float = 30.0
    item_limit: int = 50
    language: str = "en"

    def __post_init__(self) -> None:
        ua = self.user_agent.strip()
        if not ua:
            raise ValueError(
                "WikidataAdapterConfig.user_agent must be a non-empty descriptive string"
            )
        # Enforce Wikimedia User-Agent policy: must identify HullQ and include a
        # contact identifier (email address or URL).  A bare version string or
        # generic library name is insufficient.
        has_hullq = "hullq" in ua.lower()
        has_contact = bool(re.search(r"\S+@\S+\.\S+", ua) or re.search(r"https?://\S+", ua))
        if not has_hullq or not has_contact:
            raise ValueError(
                "WikidataAdapterConfig.user_agent must identify HullQ and include "
                "a contact identifier (email address or URL), per Wikimedia "
                "User-Agent policy. Example: "
                "'HullQ/0.1 (contact@example.com; https://github.com/example/hullq)'"
            )
        if not (1 <= self.item_limit <= SLICE_0008_ITEM_CEILING):
            raise ValueError(
                f"WikidataAdapterConfig.item_limit must be in [1, {SLICE_0008_ITEM_CEILING}] "
                f"(SLICE-0008 operational cap); got {self.item_limit}"
            )
        if self.request_timeout_seconds <= 0:
            raise ValueError(
                "WikidataAdapterConfig.request_timeout_seconds must be a positive number"
            )


# ---------------------------------------------------------------------------
# Acquisition error types
# ---------------------------------------------------------------------------


class WikidataAcquisitionError(Exception):
    """Base class for Wikidata adapter acquisition errors."""


class WikidataRightsBlocked(WikidataAcquisitionError):
    """Rights gate returned a non-ALLOWED outcome for automated ingestion.

    No HTTP requests are sent when this is raised.
    """

    def __init__(self, decision: SourceUseDecision) -> None:
        self.decision = decision
        super().__init__(
            f"Wikidata automated ingestion gate: {decision.outcome} — {sorted(str(r) for r in decision.reasons)}"
        )


class WikidataThrottled(WikidataAcquisitionError):
    """HTTP 429 received from Wikidata API; no retry loop is attempted."""

    def __init__(self, retry_after: str | None = None) -> None:
        self.retry_after = retry_after
        msg = "Wikidata API rate-limited (HTTP 429)"
        if retry_after:
            msg += f"; Retry-After: {retry_after}"
        super().__init__(msg)


class WikidataHTTPError(WikidataAcquisitionError):
    """Non-throttle HTTP error from Wikidata API."""

    def __init__(self, status_code: int, url: str) -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} from {url}")


class WikidataTimeout(WikidataAcquisitionError):
    """Request timed out before a response was received."""


class WikidataMalformedResponse(WikidataAcquisitionError):
    """Response JSON could not be parsed or lacks the expected structure."""


# ---------------------------------------------------------------------------
# Domain value-objects for adapter results
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WikidataEntityData:
    """Parsed, snapshot-safe entity data from the wbgetentities API.

    ``raw_claims`` is deep-copied on construction so that later mutation of
    the caller-supplied dict cannot alter the captured snapshot.
    """

    qid: str
    label: str | None
    aliases: list[str]
    raw_claims: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_claims", copy.deepcopy(self.raw_claims))
        object.__setattr__(self, "aliases", list(self.aliases))


@dataclass
class WikidataQualityReport:
    """Coverage/quality metrics for a controlled Wikidata probe run.

    ``field_presence`` maps each HullQ field label to the count of entities
    for which at least one valid mapped statement was extracted.
    ``malformed_statement_count`` counts statements skipped due to
    unrecognised snak type, unparseable quantity amount, or invalid structure.
    ``unsupported_qualifier_count`` counts statements that had unrecognised or
    absent P642 qualifier values and were therefore not mapped to a field.
    ``retrieval_count_attributed`` is the number of HTTP requests attributed
    to the Wikidata source_id during this probe.
    """

    source_id: str
    requested_qid_count: int
    fetched_entity_count: int
    field_presence: dict[str, int]
    malformed_statement_count: int
    unsupported_qualifier_count: int
    retrieval_count_attributed: int


@dataclass(frozen=True)
class WikidataProbeResult:
    """Aggregated result of a single controlled Wikidata probe run."""

    decision: SourceUseDecision
    entities: list[WikidataEntityData]
    evidence: list[FieldEvidence]
    quality_report: WikidataQualityReport
    usage_metrics: SourceUsageMetrics


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------


def validate_qid(qid: str) -> bool:
    """Return True if *qid* matches the valid Wikidata QID pattern (Q1, Q2, …).

    Q0 is not a valid Wikidata entity ID; the pattern requires Q followed by a
    non-zero digit and zero or more digits.
    """
    return bool(_QID_RE.match(qid))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_unit_qid(unit_uri: str) -> str | None:
    """Extract QID from a Wikidata quantity unit URI.

    Returns None for the dimensionless sentinel value "1".
    """
    if unit_uri == "1":
        return None
    m = _UNIT_URI_RE.match(unit_uri)
    return m.group(1) if m else None


def _get_claim_raw_unit(claim: dict[str, Any]) -> str | None:
    """Return the raw unit string from a quantity claim's mainsnak value.

    Returns the ``unit`` field exactly as it appears in the Wikidata API
    response (e.g. ``"1"`` or ``"http://www.wikidata.org/entity/Q11570"``),
    or ``None`` if the unit is absent, non-string, or the claim is malformed.
    Does not interpret the value — callers must compare directly.
    """
    mainsnak = claim.get("mainsnak")
    if not isinstance(mainsnak, dict):
        return None
    dv = mainsnak.get("datavalue")
    if not isinstance(dv, dict):
        return None
    val = dv.get("value")
    if not isinstance(val, dict):
        return None
    unit = val.get("unit")
    return unit if isinstance(unit, str) else None


def _claim_unit_qid(claim: dict[str, Any]) -> str | None:
    """Extract the unit QID from a quantity claim's mainsnak.

    Returns the QID string (e.g. ``"Q11570"``) for a recognisable Wikidata
    entity unit URL, or ``None`` for the dimensionless sentinel ``"1"``, an
    unrecognised URL, or a malformed/missing value.
    """
    mainsnak = claim.get("mainsnak")
    if not isinstance(mainsnak, dict):
        return None
    dv = mainsnak.get("datavalue")
    if not isinstance(dv, dict):
        return None
    val = dv.get("value")
    if not isinstance(val, dict):
        return None
    unit_uri = val.get("unit", "1")
    if not isinstance(unit_uri, str):
        return None
    return _extract_unit_qid(unit_uri)


def _make_evidence_id(qid: str, prop: str, stmt_id: str | None, index: int) -> str:
    """Build a deterministic, collision-resistant evidence ID."""
    if stmt_id:
        suffix = hashlib.sha256(stmt_id.encode()).hexdigest()[:16]
        return f"WD-{qid}-{prop}-{suffix}"
    return f"WD-{qid}-{prop}-idx{index}"


def _get_p642_qualifier_qids(qualifiers: dict[str, Any]) -> list[str]:
    """Extract all value QIDs from P642 ('of') qualifier snaks in a statement."""
    result: list[str] = []
    for snak in qualifiers.get(_QUALIFIER_OF, []):
        if not isinstance(snak, dict):
            continue
        if snak.get("snaktype") != "value":
            continue
        dv = snak.get("datavalue", {})
        if not isinstance(dv, dict):
            continue
        if dv.get("type") == "wikibase-entityid":
            val = dv.get("value", {})
            if isinstance(val, dict):
                qid_ref = val.get("id", "")
                if qid_ref:
                    result.append(qid_ref)
    return result


def _parse_quantity_amount(amount_str: str) -> Decimal | None:
    """Parse a Wikidata quantity amount string (e.g., '+12.8') to Decimal.

    Returns None for unparseable or non-finite values.
    """
    try:
        value = Decimal(amount_str.lstrip("+"))
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _build_quantity_evidence(
    qid: str,
    prop_id: str,
    claim: dict[str, Any],
    field_pointer: JsonPointer,
    field_label: str,
    retrieved_at: str,
    index: int,
    *,
    qualifier_qid: str | None = None,
    expected_quantity: Quantity | None = None,
) -> FieldEvidence | None:
    """Build FieldEvidence from a single Wikidata quantity claim.

    Returns None if the claim is malformed or not a value-type quantity snak.
    The raw Wikidata quantity/unit representation is always preserved separately
    from the normalized candidate (SLICE-0004 reused).

    When ``qualifier_qid`` is supplied (the P642 "of" qualifier value that
    determined the semantic mapping), it is preserved in the raw observation so
    that the mapping decision is fully recoverable from the evidence alone.

    When ``expected_quantity`` is supplied, a recognized unit of a different
    physical dimension (e.g., kg for a length field) is NOT normalized — the
    raw observation is preserved but no NormalizedCandidate is produced.  This
    prevents cross-dimension candidates (e.g., a mass candidate on a length
    field or a length candidate on a mass field).
    """
    stmt_id = claim.get("id") if isinstance(claim.get("id"), str) else None
    mainsnak = claim.get("mainsnak", {})
    if not isinstance(mainsnak, dict):
        return None
    if mainsnak.get("snaktype") != "value":
        return None

    datavalue = mainsnak.get("datavalue", {})
    if not isinstance(datavalue, dict):
        return None
    if datavalue.get("type") != "quantity":
        return None

    value_obj = datavalue.get("value", {})
    if not isinstance(value_obj, dict):
        return None

    amount_str = value_obj.get("amount", "")
    unit_uri = value_obj.get("unit", "1")
    if not isinstance(amount_str, str) or not isinstance(unit_uri, str):
        return None

    amount = _parse_quantity_amount(amount_str)
    if amount is None:
        return None

    unit_qid = _extract_unit_qid(unit_uri)

    # Build normalized candidate via SLICE-0004 if unit is recognized and
    # matches the expected physical quantity dimension.  A recognized unit of
    # the wrong dimension (e.g., kg on a length field) is NOT normalized —
    # only the raw observation is preserved in that case.
    normalized: NormalizedCandidate | None = None
    if unit_qid and unit_qid in _UNIT_QID_MAP:
        qty, unit_enum = _UNIT_QID_MAP[unit_qid]
        dimension_ok = expected_quantity is None or qty == expected_quantity
        if dimension_ok:
            try:
                obs = MeasurementObservation(quantity=qty, value=amount, unit=unit_enum)
                norm = normalize_measurement(obs)
                normalized = NormalizedCandidate(
                    value=norm.canonical_value,
                    unit=norm.canonical_unit,
                    method_id="hullq-measurements-1.0",
                    method_version="SLICE-0004-v1",
                )
            except (ValueError, InvalidOperation):  # fmt: skip
                normalized = None

    # Preserve raw Wikidata quantity/unit representation.  When the statement
    # was mapped via a P642 qualifier, also preserve the qualifier identity so
    # that the mapping basis (LOA vs LWL, displacement vs ballast, etc.) is
    # fully recoverable from this evidence object alone.
    raw_value: dict[str, str] = {"amount": amount_str, "unit": unit_uri}
    if qualifier_qid is not None:
        raw_value["qualifier_property"] = _QUALIFIER_OF
        raw_value["qualifier_value_id"] = qualifier_qid

    raw = RawObservation(
        kind=RawObservationKind.LITERAL,
        value=raw_value,
        unit=unit_qid,
        excerpt=None,
    )

    return FieldEvidence(
        evidence_id=_make_evidence_id(qid, prop_id, stmt_id, index),
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=qid),
        field_pointer=field_pointer,
        source_id=WIKIDATA_SOURCE_ID,
        source_locator=SourceLocator(
            page=None,
            section=None,
            anchor=None,
            table=None,
            figure=None,
            record_key=f"{qid}/{prop_id}/{stmt_id or '?'}",
        ),
        raw=raw,
        normalized_candidate=normalized,
        evidence_type=EvidenceType.API_RECORD,
        producer=_ADAPTER_PRODUCER,
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at=retrieved_at,
        confidence=ConfidenceLevel.MEDIUM,
        supersedes_evidence_id=None,
        notes=None,
    )


def _build_entity_ref_evidence(
    qid: str,
    prop_id: str,
    claim: dict[str, Any],
    field_pointer: JsonPointer,
    retrieved_at: str,
    index: int,
) -> FieldEvidence | None:
    """Build FieldEvidence for a wikibase-entityid reference claim.

    Used for manufacturer (P176) and designer (P287) statements. The raw
    observation preserves the referenced entity QID; no normalized candidate
    is produced because Brand/Organization role inference is not performed here.
    """
    stmt_id = claim.get("id") if isinstance(claim.get("id"), str) else None
    mainsnak = claim.get("mainsnak", {})
    if not isinstance(mainsnak, dict):
        return None
    if mainsnak.get("snaktype") != "value":
        return None

    datavalue = mainsnak.get("datavalue", {})
    if not isinstance(datavalue, dict):
        return None
    if datavalue.get("type") != "wikibase-entityid":
        return None

    val = datavalue.get("value", {})
    if not isinstance(val, dict):
        return None
    ref_qid = val.get("id", "")
    if not ref_qid:
        return None

    raw = RawObservation(
        kind=RawObservationKind.STRUCTURED_RECORD,
        value={"entity_id": ref_qid, "property": prop_id},
        unit=None,
        excerpt=None,
    )

    return FieldEvidence(
        evidence_id=_make_evidence_id(qid, prop_id, stmt_id, index),
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=qid),
        field_pointer=field_pointer,
        source_id=WIKIDATA_SOURCE_ID,
        source_locator=SourceLocator(
            page=None,
            section=None,
            anchor=None,
            table=None,
            figure=None,
            record_key=f"{qid}/{prop_id}/{stmt_id or '?'}",
        ),
        raw=raw,
        normalized_candidate=None,
        evidence_type=EvidenceType.API_RECORD,
        producer=_ADAPTER_PRODUCER,
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at=retrieved_at,
        confidence=ConfidenceLevel.MEDIUM,
        supersedes_evidence_id=None,
        notes=None,
    )


# ---------------------------------------------------------------------------
# Internal accumulator for extraction state
# ---------------------------------------------------------------------------


class _ExtractionState:
    """Mutable accumulator used during evidence extraction for a single probe run."""

    def __init__(self) -> None:
        self.evidence: list[FieldEvidence] = []
        self._field_qids: dict[str, set[str]] = {}
        self.malformed_count: int = 0
        self.unsupported_qualifier_count: int = 0

    def add_evidence(self, ev: FieldEvidence, field_label: str) -> None:
        self.evidence.append(ev)
        if field_label not in self._field_qids:
            self._field_qids[field_label] = set()
        self._field_qids[field_label].add(ev.subject.id)

    def field_presence(self) -> dict[str, int]:
        return {k: len(v) for k, v in self._field_qids.items()}


# ---------------------------------------------------------------------------
# Main adapter class
# ---------------------------------------------------------------------------


class WikidataAdapter:
    """Rights-gated Wikidata structured-data adapter for SLICE-0008.

    Requires:
    - A reviewed Source record with source_id == WIKIDATA_SOURCE_ID that
      satisfies the automated-ingestion rights gate.
    - A valid WikidataAdapterConfig.
    - An injected httpx.Client (allows deterministic offline testing without
      live network access).

    The SLICE-0007 automated-ingestion rights gate is checked before every
    HTTP request. If the gate outcome is not ALLOWED, WikidataRightsBlocked
    is raised and no HTTP request is sent.
    """

    def __init__(
        self,
        source: dict[str, Any],
        config: WikidataAdapterConfig,
        http_client: httpx.Client,
    ) -> None:
        if source.get("source_id") != WIKIDATA_SOURCE_ID:
            raise ValueError(
                f"Source record must have source_id={WIKIDATA_SOURCE_ID!r}; "
                f"got {source.get('source_id')!r}"
            )
        self._source = source
        self._config = config
        self._client = http_client
        self._usage = SourceUsageMetrics(
            source_id=WIKIDATA_SOURCE_ID,
            retrieval_count=0,
            extracted_record_count=0,
        )

    def _check_rights(self) -> SourceUseDecision:
        """Invoke the SLICE-0007 rights gate; raise WikidataRightsBlocked if non-ALLOWED."""
        decision = check_source_use(self._source, SourceUse.AUTOMATED_INGESTION)
        if decision.outcome != DecisionOutcome.ALLOWED:
            raise WikidataRightsBlocked(decision)
        return decision

    def _check_bulk_bootstrap_rights(self) -> SourceUseDecision:
        """SLICE-0017: verify BULK_BOOTSTRAP clearance before any bootstrap-scale
        discovery request.

        This is checked in addition to (not instead of) the AUTOMATED_INGESTION
        gate that ``_check_rights`` enforces before every HTTP request. The
        broad Tier-0 bootstrap is explicitly a bulk operation, so its own
        use-specific clearance (SOURCE_RIGHTS_POLICY.v0.1.md §5) must also be
        ALLOWED before the bootstrap discovery query is dispatched.
        """
        decision = check_source_use(self._source, SourceUse.BULK_BOOTSTRAP)
        if decision.outcome != DecisionOutcome.ALLOWED:
            raise WikidataRightsBlocked(decision)
        return decision

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self._config.user_agent}

    def _get(
        self,
        url: str,
        params: dict[str, str],
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute a single GET request, handling throttle/timeout/HTTP errors.

        Increments the retrieval counter after each successful dispatch
        (regardless of HTTP status code) so usage is attributable.
        """
        headers = {**self._headers(), **(extra_headers or {})}
        try:
            response = self._client.get(
                url,
                params=params,
                headers=headers,
                timeout=self._config.request_timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise WikidataTimeout(f"Request timed out: {exc}") from exc

        self._usage = self._usage.add(retrieval_delta=1)

        if response.status_code == 429:
            retry_after = (
                response.headers.get("Retry-After") if hasattr(response, "headers") else None
            )
            raise WikidataThrottled(retry_after)
        if response.status_code >= 400:
            raise WikidataHTTPError(response.status_code, url)

        try:
            data: dict[str, Any] = response.json()
        except Exception as exc:
            raise WikidataMalformedResponse(f"Response is not valid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise WikidataMalformedResponse(
                f"Expected JSON object at root; got {type(data).__name__}"
            )

        return data

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_sailboat_qids(self, limit: int) -> list[str]:
        """SPARQL probe for sailboat-class items (Q106179098).

        Checks the rights gate before dispatching the request.
        Returns deduplicated QIDs in the order they appear in the SPARQL
        result. ``limit`` must be in [1, config.item_limit].
        """
        if not (1 <= limit <= self._config.item_limit):
            raise ValueError(
                f"discover_sailboat_qids limit must be in [1, {self._config.item_limit}]; "
                f"got {limit}"
            )

        self._check_rights()

        query = _build_sparql_query(limit)
        data = self._get(
            _SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            extra_headers={"Accept": "application/sparql-results+json"},
        )

        bindings = data.get("results", {}).get("bindings", [])
        if not isinstance(bindings, list):
            raise WikidataMalformedResponse("SPARQL response: results.bindings is not a list")

        qids: list[str] = []
        seen: set[str] = set()
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            item_obj = binding.get("item", {})
            if not isinstance(item_obj, dict):
                continue
            uri = item_obj.get("value", "")
            if not isinstance(uri, str):
                continue
            m = _ENTITY_URI_RE.match(uri)
            if m:
                qid = m.group(1)
                if qid not in seen:
                    seen.add(qid)
                    qids.append(qid)

        return qids

    def discover_bootstrap_qids(self, limit: int) -> list[str]:
        """SLICE-0017: deterministic ordered discovery for the broad Tier-0 bootstrap.

        Bounded by ``WIKIDATA_BOOTSTRAP_SAFETY_CEILING`` — independent of
        ``config.item_limit`` (the SLICE-0008 <=100 controlled-probe cap,
        which this method does not read or mutate). Checks BULK_BOOTSTRAP
        clearance before any HTTP request, in addition to the
        AUTOMATED_INGESTION check ``_get`` implies via callers. Results are
        ordered deterministically (``ORDER BY ?item``) so repeated runs
        return the same first-N candidates in the same order.
        """
        if not (1 <= limit <= WIKIDATA_BOOTSTRAP_SAFETY_CEILING):
            raise ValueError(
                f"discover_bootstrap_qids limit must be in [1, {WIKIDATA_BOOTSTRAP_SAFETY_CEILING}]; "
                f"got {limit}"
            )

        self._check_bulk_bootstrap_rights()
        self._check_rights()

        query = _build_bootstrap_sparql_query(limit)
        data = self._get(
            _SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            extra_headers={"Accept": "application/sparql-results+json"},
        )

        bindings = data.get("results", {}).get("bindings", [])
        if not isinstance(bindings, list):
            raise WikidataMalformedResponse("SPARQL response: results.bindings is not a list")

        qids: list[str] = []
        seen: set[str] = set()
        for binding in bindings:
            if not isinstance(binding, dict):
                continue
            item_obj = binding.get("item", {})
            if not isinstance(item_obj, dict):
                continue
            uri = item_obj.get("value", "")
            if not isinstance(uri, str):
                continue
            m = _ENTITY_URI_RE.match(uri)
            if m:
                qid = m.group(1)
                if qid not in seen:
                    seen.add(qid)
                    qids.append(qid)

        return qids

    # ------------------------------------------------------------------
    # Entity acquisition
    # ------------------------------------------------------------------

    def fetch_entities(self, qids: list[str]) -> list[WikidataEntityData]:
        """Fetch structured entity data for a bounded list of QIDs.

        Validates QID syntax before any network use. Batches requests within
        the documented wbgetentities limit. Checks the rights gate before
        each batch. ``len(qids)`` must not exceed ``config.item_limit``.
        """
        return self._fetch_entities_impl(qids, self._config.item_limit)

    def fetch_entities_bootstrap(self, qids: list[str]) -> list[WikidataEntityData]:
        """SLICE-0017: fetch structured entity data at bootstrap scale.

        Identical acquisition semantics to ``fetch_entities`` (QID validation,
        batching, per-batch rights gate), bounded by
        ``WIKIDATA_BOOTSTRAP_SAFETY_CEILING`` instead of ``config.item_limit``.
        """
        return self._fetch_entities_impl(qids, WIKIDATA_BOOTSTRAP_SAFETY_CEILING)

    def _fetch_entities_impl(self, qids: list[str], max_allowed: int) -> list[WikidataEntityData]:
        invalid = [q for q in qids if not validate_qid(q)]
        if invalid:
            raise ValueError(f"Invalid QID format(s) before network use: {invalid!r}")

        if len(qids) > max_allowed:
            raise ValueError(f"Requested {len(qids)} QIDs exceeds allowed limit {max_allowed}")

        # Deduplicate preserving order (exact QID identity, no merge).
        seen: set[str] = set()
        deduped: list[str] = []
        for q in qids:
            if q not in seen:
                seen.add(q)
                deduped.append(q)

        entities: list[WikidataEntityData] = []
        for i in range(0, len(deduped), _ENTITY_API_BATCH_SIZE):
            batch = deduped[i : i + _ENTITY_API_BATCH_SIZE]
            self._check_rights()
            lang = self._config.language
            languages_param = lang if lang == "en" else f"{lang}|en"
            data = self._get(
                _ENTITY_API_ENDPOINT,
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(batch),
                    "format": "json",
                    "languages": languages_param,
                    "props": "labels|aliases|claims",
                },
            )
            raw_entities = data.get("entities")
            if not isinstance(raw_entities, dict):
                raise WikidataMalformedResponse("wbgetentities response missing 'entities' object")
            for qid in batch:
                entity_raw = raw_entities.get(qid)
                if not isinstance(entity_raw, dict):
                    continue
                if entity_raw.get("type") != "item":
                    continue
                entities.append(self._parse_entity(qid, entity_raw))
                self._usage = self._usage.add(extracted_delta=1)

        return entities

    def _parse_entity(self, qid: str, raw: dict[str, Any]) -> WikidataEntityData:
        lang = self._config.language

        labels = raw.get("labels", {})
        if not isinstance(labels, dict):
            labels = {}
        label_obj = labels.get(lang) or labels.get("en")
        label: str | None = None
        if isinstance(label_obj, dict):
            lv = label_obj.get("value")
            label = lv if isinstance(lv, str) else None

        aliases_raw = raw.get("aliases") or {}
        if not isinstance(aliases_raw, dict):
            aliases_raw = {}
        lang_aliases = aliases_raw.get(lang, []) or aliases_raw.get("en", [])
        if not isinstance(lang_aliases, list):
            lang_aliases = []
        aliases = [
            a["value"]
            for a in lang_aliases
            if isinstance(a, dict) and isinstance(a.get("value"), str)
        ]

        claims = raw.get("claims", {})
        if not isinstance(claims, dict):
            claims = {}

        return WikidataEntityData(qid=qid, label=label, aliases=aliases, raw_claims=claims)

    # ------------------------------------------------------------------
    # Field evidence extraction
    # ------------------------------------------------------------------

    def extract_field_evidence(
        self,
        entities: list[WikidataEntityData],
        retrieved_at: str,
        *,
        requested_qid_count: int,
    ) -> tuple[list[FieldEvidence], WikidataQualityReport]:
        """Extract FieldEvidence candidates from acquired entities.

        ``requested_qid_count`` must be the number of distinct QIDs that were
        submitted to fetch_entities (post-deduplication), as tracked by the
        caller before the API call.  It is distinct from ``fetched_entity_count``
        (the number of usable item-type entities actually returned by the API),
        which may be lower when QIDs are absent or of a non-item type.

        No canonical FieldResolution or BoatDesign write is performed.
        SLICE-0004 normalization is reused for recognised quantity units.
        Statements with absent or unsupported qualifiers are routed to the
        unsupported count rather than guessed.
        """
        state = _ExtractionState()

        for entity in entities:
            self._extract_entity_evidence(entity, retrieved_at, state)

        report = WikidataQualityReport(
            source_id=WIKIDATA_SOURCE_ID,
            requested_qid_count=requested_qid_count,
            fetched_entity_count=len(entities),
            field_presence=state.field_presence(),
            malformed_statement_count=state.malformed_count,
            unsupported_qualifier_count=state.unsupported_qualifier_count,
            retrieval_count_attributed=self._usage.retrieval_count,
        )

        return state.evidence, report

    def _extract_entity_evidence(
        self,
        entity: WikidataEntityData,
        retrieved_at: str,
        state: _ExtractionState,
    ) -> None:
        qid = entity.qid
        claims = entity.raw_claims

        # P176: manufacturer — entity reference, no role inference
        self._process_entity_refs(
            qid,
            _PROP_MANUFACTURER,
            claims,
            _PTR_BUILDERS,
            "manufacturer",
            retrieved_at,
            state,
        )

        # P287: designer — entity reference, no role inference
        self._process_entity_refs(
            qid,
            _PROP_DESIGNER,
            claims,
            _PTR_DESIGNERS,
            "designer",
            retrieved_at,
            state,
        )

        # P2043: length — qualifier distinguishes LOA vs LWL; all must be LENGTH
        self._process_qualified_quantity(
            qid,
            _PROP_LENGTH,
            claims,
            {_QUAL_LOA: (_PTR_LOA, "loa"), _QUAL_LWL: (_PTR_LWL, "lwl")},
            retrieved_at,
            state,
            expected_quantity=Quantity.LENGTH,
        )

        # P2049: beam/width — no qualifier required; must be LENGTH
        self._process_unqualified_quantity(
            qid,
            _PROP_WIDTH,
            claims,
            _PTR_BEAM,
            "beam",
            retrieved_at,
            state,
            expected_quantity=Quantity.LENGTH,
        )

        # P2048: height — qualifier distinguishes draft; others are unsupported; must be LENGTH
        self._process_qualified_quantity(
            qid,
            _PROP_HEIGHT,
            claims,
            {_QUAL_DRAFT: (_PTR_DRAFT, "draft")},
            retrieved_at,
            state,
            expected_quantity=Quantity.LENGTH,
        )

        # P2067: mass — qualifier distinguishes displacement vs ballast; all must be MASS
        self._process_qualified_quantity(
            qid,
            _PROP_MASS,
            claims,
            {
                _QUAL_DISPLACEMENT: (_PTR_DISPLACEMENT, "displacement"),
                _QUAL_BALLAST: (_PTR_BALLAST, "ballast"),
            },
            retrieved_at,
            state,
            expected_quantity=Quantity.MASS,
        )

        # P1092: total produced — dimensionless count; dimensional units → unsupported
        self._process_count_quantity(
            qid,
            _PROP_TOTAL_PRODUCED,
            claims,
            _PTR_NUMBER_BUILT,
            "total_produced",
            retrieved_at,
            state,
        )

    def _process_entity_refs(
        self,
        qid: str,
        prop_id: str,
        claims: dict[str, Any],
        field_pointer: JsonPointer,
        field_label: str,
        retrieved_at: str,
        state: _ExtractionState,
    ) -> None:
        prop_claims = claims.get(prop_id, [])
        if not isinstance(prop_claims, list):
            return
        for idx, claim in enumerate(prop_claims):
            if not isinstance(claim, dict):
                state.malformed_count += 1
                continue
            ev = _build_entity_ref_evidence(qid, prop_id, claim, field_pointer, retrieved_at, idx)
            if ev is None:
                # novalue/somevalue snaks are not malformed — skip without penalty
                mainsnak = claim.get("mainsnak", {})
                if isinstance(mainsnak, dict) and mainsnak.get("snaktype") in (
                    "novalue",
                    "somevalue",
                ):
                    continue
                state.malformed_count += 1
            else:
                state.add_evidence(ev, field_label)

    def _process_unqualified_quantity(
        self,
        qid: str,
        prop_id: str,
        claims: dict[str, Any],
        field_pointer: JsonPointer,
        field_label: str,
        retrieved_at: str,
        state: _ExtractionState,
        *,
        expected_quantity: Quantity | None = None,
    ) -> None:
        """Process quantity claims that need no qualifier disambiguation.

        When ``expected_quantity`` is supplied, any claim whose unit resolves to
        a recognised Wikidata entity QID of the wrong physical dimension is routed
        to ``unsupported_qualifier_count`` and produces NO FieldEvidence.
        Unrecognised units are not rejected — they pass through to
        ``_build_quantity_evidence`` and produce raw evidence without a
        NormalizedCandidate, preserving the existing unknown-unit contract.
        """
        prop_claims = claims.get(prop_id, [])
        if not isinstance(prop_claims, list):
            return
        for idx, claim in enumerate(prop_claims):
            if not isinstance(claim, dict):
                state.malformed_count += 1
                continue
            # Reject a recognised wrong-dimension unit before creating any evidence.
            if expected_quantity is not None:
                unit_qid = _claim_unit_qid(claim)
                if unit_qid is not None and unit_qid in _UNIT_QID_MAP:
                    actual_qty, _ = _UNIT_QID_MAP[unit_qid]
                    if actual_qty != expected_quantity:
                        state.unsupported_qualifier_count += 1
                        continue
            ev = _build_quantity_evidence(
                qid,
                prop_id,
                claim,
                field_pointer,
                field_label,
                retrieved_at,
                idx,
                expected_quantity=expected_quantity,
            )
            if ev is None:
                mainsnak = claim.get("mainsnak", {})
                if isinstance(mainsnak, dict) and mainsnak.get("snaktype") in (
                    "novalue",
                    "somevalue",
                ):
                    continue
                state.malformed_count += 1
            else:
                state.add_evidence(ev, field_label)

    def _process_count_quantity(
        self,
        qid: str,
        prop_id: str,
        claims: dict[str, Any],
        field_pointer: JsonPointer,
        field_label: str,
        retrieved_at: str,
        state: _ExtractionState,
    ) -> None:
        """Process dimensionless integer-count claims (e.g. P1092 total produced).

        Acceptance is exact: only the literal Wikidata dimensionless sentinel
        ``"1"`` produces ``number_built`` FieldEvidence.

        - ``unit == "1"``          → raw count evidence (no NormalizedCandidate)
        - ``unit`` is a QID URL    → ``unsupported_qualifier_count`` incremented
        - ``unit`` is any other URL → ``unsupported_qualifier_count`` incremented
        - ``unit`` missing / non-str → ``malformed_count`` incremented

        ``_claim_unit_qid()`` is intentionally NOT used here because it returns
        ``None`` for both ``"1"`` and for non-QID URLs, making those two cases
        indistinguishable.  ``_get_claim_raw_unit()`` returns the literal string
        for direct comparison.
        """
        prop_claims = claims.get(prop_id, [])
        if not isinstance(prop_claims, list):
            return
        for idx, claim in enumerate(prop_claims):
            if not isinstance(claim, dict):
                state.malformed_count += 1
                continue
            mainsnak = claim.get("mainsnak", {})
            if isinstance(mainsnak, dict) and mainsnak.get("snaktype") in ("novalue", "somevalue"):
                continue
            raw_unit = _get_claim_raw_unit(claim)
            if raw_unit is None:
                # Missing or non-string unit — malformed statement
                state.malformed_count += 1
                continue
            if raw_unit != "1":
                # Any unit other than the exact dimensionless sentinel — unsupported
                state.unsupported_qualifier_count += 1
                continue
            ev = _build_quantity_evidence(
                qid,
                prop_id,
                claim,
                field_pointer,
                field_label,
                retrieved_at,
                idx,
                expected_quantity=None,
            )
            if ev is None:
                state.malformed_count += 1
            else:
                state.add_evidence(ev, field_label)

    def _process_qualified_quantity(
        self,
        qid: str,
        prop_id: str,
        claims: dict[str, Any],
        qualifier_map: dict[str, tuple[JsonPointer, str]],
        retrieved_at: str,
        state: _ExtractionState,
        *,
        expected_quantity: Quantity | None = None,
    ) -> None:
        """Process quantity claims where a P642 qualifier determines field mapping.

        Statements with absent or unrecognised qualifier values are counted as
        unsupported rather than guessed.  ``expected_quantity`` is forwarded to
        ``_build_quantity_evidence`` to prevent cross-dimension normalisation.
        """
        prop_claims = claims.get(prop_id, [])
        if not isinstance(prop_claims, list):
            return
        for idx, claim in enumerate(prop_claims):
            if not isinstance(claim, dict):
                state.malformed_count += 1
                continue

            mainsnak = claim.get("mainsnak", {})
            if isinstance(mainsnak, dict) and mainsnak.get("snaktype") in ("novalue", "somevalue"):
                continue

            qualifiers = claim.get("qualifiers", {})
            if not isinstance(qualifiers, dict):
                qualifiers = {}

            qual_qids = _get_p642_qualifier_qids(qualifiers)
            matched = False
            for qual_qid in qual_qids:
                if qual_qid in qualifier_map:
                    field_pointer, field_label = qualifier_map[qual_qid]
                    # Reject a recognised wrong-dimension unit before creating evidence.
                    if expected_quantity is not None:
                        unit_qid = _claim_unit_qid(claim)
                        if unit_qid is not None and unit_qid in _UNIT_QID_MAP:
                            actual_qty, _ = _UNIT_QID_MAP[unit_qid]
                            if actual_qty != expected_quantity:
                                state.unsupported_qualifier_count += 1
                                matched = True
                                break
                    ev = _build_quantity_evidence(
                        qid,
                        prop_id,
                        claim,
                        field_pointer,
                        field_label,
                        retrieved_at,
                        idx,
                        qualifier_qid=qual_qid,
                        expected_quantity=expected_quantity,
                    )
                    if ev is None:
                        state.malformed_count += 1
                    else:
                        state.add_evidence(ev, field_label)
                    matched = True
                    break

            if not matched:
                state.unsupported_qualifier_count += 1

    # ------------------------------------------------------------------
    # Combined probe entry point
    # ------------------------------------------------------------------

    def run_controlled_probe(
        self,
        *,
        discovery_limit: int | None = None,
        explicit_qids: list[str] | None = None,
        retrieved_at: str,
    ) -> WikidataProbeResult:
        """Run the full controlled probe pipeline.

        Either ``explicit_qids`` or a SPARQL discovery with ``discovery_limit``
        determines the input QID set. The rights gate is checked before any
        HTTP use. Quality report counts are computed after extraction.
        """
        decision = self._check_rights()

        if explicit_qids is not None:
            # Deduplicate preserving order; requested_qid_count is the distinct
            # count after exact-QID deduplication — i.e., what is actually
            # submitted to fetch_entities and thus to the Wikidata API.
            seen: set[str] = set()
            deduped: list[str] = []
            for q in explicit_qids:
                if q not in seen:
                    seen.add(q)
                    deduped.append(q)
            requested_count = len(deduped)
            entities = self.fetch_entities(deduped)
        else:
            effective_limit = (
                discovery_limit if discovery_limit is not None else self._config.item_limit
            )
            qids = self.discover_sailboat_qids(effective_limit)
            # discover_sailboat_qids already deduplicates; requested_count is the
            # number of discovered QIDs submitted to fetch_entities.
            requested_count = len(qids)
            entities = self.fetch_entities(qids) if qids else []

        evidence, report = self.extract_field_evidence(
            entities, retrieved_at, requested_qid_count=requested_count
        )

        return WikidataProbeResult(
            decision=decision,
            entities=entities,
            evidence=evidence,
            quality_report=report,
            usage_metrics=self._usage,
        )

    @property
    def usage_metrics(self) -> SourceUsageMetrics:
        """Current cumulative usage metrics attributed to WIKIDATA_SOURCE_ID."""
        return self._usage
