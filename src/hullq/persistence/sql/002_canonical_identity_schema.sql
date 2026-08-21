-- HullQ canonical identity persistence schema — SLICE-0016
-- Migration 002: adds the Tier-0 canonical identity persistence boundary on
-- top of the accepted SLICE-0013 research-persistence schema. Extends the
-- existing migration chain; research_observations / research_evidence /
-- research_bundles are unchanged and are only referenced here by foreign key.
--
-- Immutable identity semantics:
--   Every canonical entity/relationship/alias/link row is caller-supplied,
--   stable and immutable (IDENTITY_MODEL.v0.2 / ADR-0011). No column here
--   mints or derives an ID from a display name or external/source ID.
--   content_hash columns enforce fail-closed collision detection at import
--   time, exactly like research_observations/research_evidence in migration
--   001. Two distinct entity IDs MAY share a visible canonical_name; no
--   uniqueness constraint is placed on any name column.
--
-- Provenance linkage:
--   canonical_admission_evidence_links references research_observations /
--   research_evidence by their existing stable IDs. It intentionally has NO
--   foreign key into bundle_reference_crosschecks — a reference crosscheck
--   structurally cannot satisfy canonical admission provenance.

CREATE TABLE canonical_brands (
    id              TEXT        NOT NULL,
    canonical_name  TEXT        NOT NULL,
    content_hash    TEXT        NOT NULL,
    admitted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id)
);

CREATE TABLE canonical_organizations (
    id              TEXT        NOT NULL,
    canonical_name  TEXT        NOT NULL,
    content_hash    TEXT        NOT NULL,
    admitted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id)
);

-- Entity-scoped aliases (IDENTITY_ALIAS_SCHEMA.v0.1). alias_id is stable only
-- within the owning entity's scope; the same alias_id string may legitimately
-- repeat under a different owning entity without collision.
CREATE TABLE canonical_brand_aliases (
    brand_id      TEXT NOT NULL,
    alias_id      TEXT NOT NULL,
    alias_class   TEXT NOT NULL,
    name          TEXT NOT NULL,
    notes         TEXT,
    content_hash  TEXT NOT NULL,
    PRIMARY KEY (brand_id, alias_id),
    CONSTRAINT fk_cba_brand
        FOREIGN KEY (brand_id) REFERENCES canonical_brands (id)
);

CREATE TABLE canonical_organization_aliases (
    organization_id TEXT NOT NULL,
    alias_id        TEXT NOT NULL,
    alias_class     TEXT NOT NULL,
    name            TEXT NOT NULL,
    notes           TEXT,
    content_hash    TEXT NOT NULL,
    PRIMARY KEY (organization_id, alias_id),
    CONSTRAINT fk_coa_organization
        FOREIGN KEY (organization_id) REFERENCES canonical_organizations (id)
);

CREATE TABLE canonical_boat_models (
    id              TEXT        NOT NULL,
    canonical_name  TEXT        NOT NULL,
    first_built     INTEGER,
    last_built      INTEGER,
    content_hash    TEXT        NOT NULL,
    admitted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id)
);

CREATE TABLE canonical_boat_model_aliases (
    boat_model_id TEXT NOT NULL,
    alias_id      TEXT NOT NULL,
    alias_class   TEXT NOT NULL,
    name          TEXT NOT NULL,
    notes         TEXT,
    content_hash  TEXT NOT NULL,
    PRIMARY KEY (boat_model_id, alias_id),
    CONSTRAINT fk_cbma_boat_model
        FOREIGN KEY (boat_model_id) REFERENCES canonical_boat_models (id)
);

-- Standalone Brand<->BoatModel relationship rows (BRAND_MODEL_RELATIONSHIP_SCHEMA.v0.1).
-- Extracted from the embedded brand_relationships array on a BoatModel v0.2
-- payload; boat_model_id is supplied from the enclosing admission context,
-- never trusted from caller-embedded data (the embedded schema form
-- intentionally omits it to avoid contradictory cross-ID claims).
CREATE TABLE canonical_brand_model_relationships (
    id               TEXT NOT NULL,
    brand_id         TEXT NOT NULL,
    boat_model_id    TEXT NOT NULL,
    first_year       INTEGER,
    last_year        INTEGER,
    hull_number_from TEXT,
    hull_number_to   TEXT,
    market           TEXT,
    notes            TEXT,
    content_hash     TEXT NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_cbmr_brand
        FOREIGN KEY (brand_id) REFERENCES canonical_brands (id),
    CONSTRAINT fk_cbmr_boat_model
        FOREIGN KEY (boat_model_id) REFERENCES canonical_boat_models (id)
);

-- BoatDesign v0.5 Tier-0 identity + technical baseline. named_variants and
-- design_options are persisted opaquely as JSONB: SLICE-0016 scope requires
-- the full accepted BoatDesign payload to round-trip losslessly (they are
-- required schema keys), but NamedVariant/DesignOption normalized/queryable
-- persistence is explicitly out of scope for this slice.
CREATE TABLE canonical_boat_designs (
    id               TEXT        NOT NULL,
    boat_model_id    TEXT        NOT NULL,
    generation       JSONB       NOT NULL,
    designers        JSONB       NOT NULL,
    number_built     INTEGER,
    baseline         JSONB       NOT NULL,
    named_variants   JSONB       NOT NULL,
    design_options   JSONB       NOT NULL,
    quality          JSONB       NOT NULL,
    content_hash     TEXT        NOT NULL,
    admitted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id),
    CONSTRAINT fk_cbd_boat_model
        FOREIGN KEY (boat_model_id) REFERENCES canonical_boat_models (id)
);

-- Standalone Organization<->BoatDesign builder/manufacturer relationship rows
-- (ORGANIZATION_DESIGN_RELATIONSHIP_SCHEMA.v0.1). Extracted from the embedded
-- relationships.builders array on a BoatDesign v0.5 payload; boat_design_id
-- is supplied from the enclosing admission context. A builder change alone
-- never creates a new BoatDesign row (ADR-0004) — it only ever changes rows
-- in this table.
CREATE TABLE canonical_organization_design_relationships (
    id               TEXT NOT NULL,
    organization_id  TEXT NOT NULL,
    boat_design_id   TEXT NOT NULL,
    role             TEXT NOT NULL,
    first_year       INTEGER,
    last_year        INTEGER,
    hull_number_from TEXT,
    hull_number_to   TEXT,
    market           TEXT,
    notes            TEXT,
    content_hash     TEXT NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_codr_organization
        FOREIGN KEY (organization_id) REFERENCES canonical_organizations (id),
    CONSTRAINT fk_codr_boat_design
        FOREIGN KEY (boat_design_id) REFERENCES canonical_boat_designs (id)
);

-- Canonical admission provenance linkage. Exactly one of observation_id /
-- evidence_id must be set: a link addresses one retained HullQ research
-- record, never a positional array slot. There is deliberately no foreign
-- key into bundle_reference_crosschecks (crosschecks cannot satisfy
-- canonical admission provenance).
CREATE TABLE canonical_admission_evidence_links (
    link_id         TEXT        NOT NULL,
    entity_kind     TEXT        NOT NULL,
    entity_id       TEXT        NOT NULL,
    observation_id  TEXT,
    evidence_id     TEXT,
    notes           TEXT,
    content_hash    TEXT        NOT NULL,
    admitted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (link_id),
    CONSTRAINT fk_cael_observation
        FOREIGN KEY (observation_id) REFERENCES research_observations (observation_id),
    CONSTRAINT fk_cael_evidence
        FOREIGN KEY (evidence_id) REFERENCES research_evidence (evidence_id),
    CONSTRAINT chk_cael_exactly_one_reference CHECK (
        (CASE WHEN observation_id IS NOT NULL THEN 1 ELSE 0 END)
      + (CASE WHEN evidence_id IS NOT NULL THEN 1 ELSE 0 END) = 1
    )
);

CREATE INDEX idx_cael_entity ON canonical_admission_evidence_links (entity_kind, entity_id);
