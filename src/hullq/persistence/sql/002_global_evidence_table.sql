-- HullQ migration 002: Global FieldEvidence v0.3 identity — SLICE-0013 review fix
--
-- Replaces bundle-scoped bundle_promoted_evidence with:
--   research_evidence      (global immutable table; PK = evidence_id)
--   bundle_evidence_members (membership/link table; mirrors bundle_observation_members)
--
-- Same identity semantics as research_observations:
--   same evidence_id + same semantic content   → reusable across bundles (ALREADY_IMPORTED)
--   same evidence_id + different content       → CONFLICT (fail-closed)
--
-- SailboatData field values are NOT stored here.
-- No canonical subject entity table is introduced (subject_kind / subject_id text columns).

CREATE TABLE research_evidence (
    evidence_id             TEXT        NOT NULL,
    content_hash            TEXT        NOT NULL,
    subject_kind            TEXT        NOT NULL,
    subject_id              TEXT        NOT NULL,
    field_pointer           TEXT        NOT NULL,
    source_id               TEXT        NOT NULL,
    source_locator          JSONB       NOT NULL,
    raw_observation         JSONB       NOT NULL,
    normalized_candidate    JSONB,
    evidence_type           TEXT        NOT NULL,
    claim_semantics         TEXT        NOT NULL,
    applicability           JSONB       NOT NULL,
    producer                JSONB       NOT NULL,
    research_context        JSONB       NOT NULL,
    observed_at             TEXT        NOT NULL,
    confidence              TEXT        NOT NULL,
    supersedes_evidence_id  TEXT,
    notes                   TEXT,
    first_recorded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (evidence_id)
);

-- Bundle ↔ evidence membership (one evidence row may appear in multiple bundles)
CREATE TABLE bundle_evidence_members (
    bundle_id       TEXT NOT NULL,
    bundle_version  TEXT NOT NULL,
    evidence_id     TEXT NOT NULL,
    PRIMARY KEY (bundle_id, bundle_version, evidence_id),
    CONSTRAINT fk_bem_bundle
        FOREIGN KEY (bundle_id, bundle_version)
        REFERENCES research_bundles (bundle_id, bundle_version),
    CONSTRAINT fk_bem_evidence
        FOREIGN KEY (evidence_id)
        REFERENCES research_evidence (evidence_id)
);

-- Remove bundle-scoped evidence table (replaced by global research_evidence above)
DROP TABLE bundle_promoted_evidence;
