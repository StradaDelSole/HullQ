-- HullQ initial research persistence schema — SLICE-0013
-- Migration 001: creates all tables for ResearchEvidenceBundle persistence.
--
-- Immutable identity semantics:
--   (bundle_id, bundle_version) is the PRIMARY KEY for research_bundles.
--   observation_id is the PRIMARY KEY for research_observations (shared global table).
--   content_hash columns enforce fail-closed collision detection at import time.
--
-- Reference crosschecks intentionally have NO evidence_id column and no foreign
-- key into any evidence table. This structural separation prevents crosschecks
-- from satisfying FieldResolution evidence references.

-- Versioned bundle snapshots (one row per (bundle_id, bundle_version) pair)
CREATE TABLE research_bundles (
    bundle_id       TEXT        NOT NULL,
    bundle_version  TEXT        NOT NULL,
    content_hash    TEXT        NOT NULL,
    schema_version  TEXT        NOT NULL DEFAULT '0.1',
    research_target JSONB       NOT NULL,
    research_job_id TEXT,
    activity_id     TEXT,
    imported_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (bundle_id, bundle_version)
);

-- Global research observations (shared across bundles; identity is observation_id)
CREATE TABLE research_observations (
    observation_id                TEXT        NOT NULL,
    content_hash                  TEXT        NOT NULL,
    research_target               JSONB       NOT NULL,
    source_id                     TEXT        NOT NULL,
    source_locator                JSONB       NOT NULL,
    raw_observation               JSONB       NOT NULL,
    normalized_candidate          JSONB,
    evidence_type                 TEXT        NOT NULL,
    claim_semantics               TEXT        NOT NULL,
    applicability                 JSONB       NOT NULL,
    producer                      JSONB       NOT NULL,
    research_context              JSONB       NOT NULL,
    observed_at                   TEXT        NOT NULL,
    confidence                    TEXT        NOT NULL,
    supersedes_observation_id     TEXT,
    intended_subject_kind_hint    TEXT,
    intended_field_pointer        TEXT,
    notes                         TEXT,
    first_recorded_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (observation_id)
);

-- Bundle ↔ observation membership (one observation may appear in multiple bundles)
CREATE TABLE bundle_observation_members (
    bundle_id       TEXT NOT NULL,
    bundle_version  TEXT NOT NULL,
    observation_id  TEXT NOT NULL,
    PRIMARY KEY (bundle_id, bundle_version, observation_id),
    CONSTRAINT fk_bom_bundle
        FOREIGN KEY (bundle_id, bundle_version)
        REFERENCES research_bundles (bundle_id, bundle_version),
    CONSTRAINT fk_bom_observation
        FOREIGN KEY (observation_id)
        REFERENCES research_observations (observation_id)
);

-- Unresolved findings (scoped to a bundle version)
CREATE TABLE bundle_unresolved_findings (
    finding_id              TEXT  NOT NULL,
    bundle_id               TEXT  NOT NULL,
    bundle_version          TEXT  NOT NULL,
    topic                   TEXT  NOT NULL,
    description             TEXT  NOT NULL,
    severity                TEXT  NOT NULL,
    related_observation_ids JSONB NOT NULL,
    PRIMARY KEY (finding_id, bundle_id, bundle_version),
    CONSTRAINT fk_buf_bundle
        FOREIGN KEY (bundle_id, bundle_version)
        REFERENCES research_bundles (bundle_id, bundle_version)
);

-- Reference crosschecks — structurally outside HullQ evidence/provenance.
-- No evidence_id column. No foreign key into evidence tables.
-- SailboatData field values are NOT stored here.
CREATE TABLE bundle_reference_crosschecks (
    crosscheck_id         TEXT NOT NULL,
    bundle_id             TEXT NOT NULL,
    bundle_version        TEXT NOT NULL,
    reference_source_id   TEXT NOT NULL,
    topic_or_field        TEXT,
    outcome               TEXT NOT NULL,
    notes                 TEXT,
    PRIMARY KEY (crosscheck_id, bundle_id, bundle_version),
    CONSTRAINT fk_brc_bundle
        FOREIGN KEY (bundle_id, bundle_version)
        REFERENCES research_bundles (bundle_id, bundle_version)
);

-- Optional already-promoted FieldEvidence v0.3 (per bundle version)
-- subject_kind / subject_id represent the typed canonical subject without
-- requiring a canonical entity table in this slice.
CREATE TABLE bundle_promoted_evidence (
    evidence_id             TEXT        NOT NULL,
    bundle_id               TEXT        NOT NULL,
    bundle_version          TEXT        NOT NULL,
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
    PRIMARY KEY (evidence_id, bundle_id, bundle_version),
    CONSTRAINT fk_bpe_bundle
        FOREIGN KEY (bundle_id, bundle_version)
        REFERENCES research_bundles (bundle_id, bundle_version)
);
