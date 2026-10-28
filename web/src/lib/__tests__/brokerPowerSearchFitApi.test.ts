// SLICE-0095 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `fetchPowerSearchFit`'s real-HTTP-status classification and --
// like `brokerSearchFitApi.test.ts`'s identical discipline for the
// structurally separate Sail preview -- that a malformed or
// unexpected-shape JSON body degrades to `{kind: "service_error"}` rather
// than throwing, against a tiny local http server standing in for
// FastAPI's `/api/broker/organizations/{id}/inventory/{listing}/power-search-fit`
// route.
//
// Independent review amendment Finding A (round 1): the original
// `VALID_CLAIM_ONLY_VIEW` fixture was itself internally INVALID (two
// `active_requirement` keys for a drive-only request, one evidence leaf)
// and the validator at the time accepted it anyway. Every "valid" fixture
// below is now genuinely self-consistent with the request it answers, and
// a battery of adversarial mutations of it (cross-listing, changed value,
// extra/missing active_requirement key, missing/swapped leaf, incoherent
// source/category/result, impossible TRUE aggregate) is asserted to
// collapse to `service_error`.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  fetchPowerSearchFit,
  type PowerSearchFitView,
} from "../brokerPowerSearchFitApi.ts";

async function withServer(
  handler: http.RequestListener,
  run: (baseUrl: string) => Promise<void>,
): Promise<void> {
  const server = http.createServer(handler);
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const address = server.address();
    if (address === null || typeof address === "string") {
      throw new Error("expected a bound TCP address");
    }
    await run(`http://127.0.0.1:${address.port}`);
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
}

function jsonResponse(res: http.ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

// Genuinely self-consistent: a drive-ONLY request ({ powerDrive: "SHAFT" }),
// exactly one active_requirement key, exactly one matching TRUE evidence
// leaf, claim-only (no design_evaluation, source_basis=PUBLISHER_CLAIM),
// no exclusion, no blockers.
const VALID_CLAIM_ONLY_VIEW: PowerSearchFitView = {
  native_listing_id: "NL-1",
  domain: "POWER",
  active_requirement: { power_drive: "SHAFT" },
  result_class: "CONFIRMED_MATCH",
  design_evaluation: null,
  design_configuration_evidence: [],
  criterion_evidence: [
    {
      criterion: { kind: "CATEGORICAL", field: "power_drive_configuration", equals: "SHAFT" },
      field: "power_drive_configuration",
      truth: "TRUE",
      reason: null,
      explanation: "power_drive_configuration=SHAFT satisfies SHAFT",
      observed_value: "SHAFT",
    },
  ],
  vessel_category_exclusion: null,
  source_basis: "PUBLISHER_CLAIM",
  blockers: [],
};

// Genuinely self-consistent combined (drive+count) design-linked match.
const VALID_DESIGN_LINKED_VIEW: PowerSearchFitView = {
  native_listing_id: "NL-1",
  domain: "POWER",
  active_requirement: { power_drive: "SHAFT", power_engine_count: "2" },
  result_class: "CONFIRMED_MATCH",
  design_evaluation: {
    design_id: "BD-1",
    result_class: "CONFIRMED_MATCH",
    matching_configuration_ids: ["BD-1::baseline"],
    reason: null,
  },
  design_configuration_evidence: [
    {
      configuration_id: "BD-1::baseline",
      boat_design_id: "BD-1",
      named_variant_id: null,
      truth: "TRUE",
      criterion_evidence: [
        {
          criterion: { kind: "CATEGORICAL", field: "power_drive_configuration", equals: "SHAFT" },
          field: "power_drive_configuration",
          truth: "TRUE",
          reason: null,
          explanation: "design value SHAFT satisfies SHAFT",
          observed_value: "SHAFT",
        },
        {
          criterion: {
            kind: "NUMERIC",
            field: "power_engine_count",
            comparison: "RANGE",
            threshold_min: "2",
            threshold_max: "2",
          },
          field: "power_engine_count",
          truth: "TRUE",
          reason: null,
          explanation: "design value 2 satisfies 2",
          observed_value: "2",
        },
      ],
    },
  ],
  criterion_evidence: [
    {
      criterion: { kind: "CATEGORICAL", field: "power_drive_configuration", equals: "SHAFT" },
      field: "power_drive_configuration",
      truth: "TRUE",
      reason: null,
      explanation: "power_drive_configuration=SHAFT satisfies SHAFT",
      observed_value: "SHAFT",
    },
    {
      criterion: {
        kind: "NUMERIC",
        field: "power_engine_count",
        comparison: "RANGE",
        threshold_min: "2",
        threshold_max: "2",
      },
      field: "power_engine_count",
      truth: "TRUE",
      reason: null,
      explanation: "power_engine_count=2 satisfies 2",
      observed_value: "2",
    },
  ],
  vessel_category_exclusion: null,
  source_basis: null,
  blockers: [],
};

// Independent review amendment Finding F (round 2): a genuinely valid
// design-linked MATCH where TWO configurations (baseline + a NamedVariant)
// are each independently TRUE -- `matching_configuration_ids` must list
// BOTH, not merely one of them, for the view to be accepted.
const SECOND_TRUE_CONFIG = {
  configuration_id: "BD-1::NV-1",
  boat_design_id: "BD-1",
  named_variant_id: "NV-1",
  truth: "TRUE" as const,
  criterion_evidence: VALID_DESIGN_LINKED_VIEW.design_configuration_evidence[0].criterion_evidence,
};
const VALID_DESIGN_LINKED_TWO_CONFIG_MATCH_VIEW: PowerSearchFitView = {
  ...VALID_DESIGN_LINKED_VIEW,
  design_evaluation: {
    ...VALID_DESIGN_LINKED_VIEW.design_evaluation!,
    matching_configuration_ids: ["BD-1::baseline", "BD-1::NV-1"],
  },
  design_configuration_evidence: [
    VALID_DESIGN_LINKED_VIEW.design_configuration_evidence[0],
    SECOND_TRUE_CONFIG,
  ],
};

// A genuinely valid design-linked CONFIRMED_NON_MATCH: every configuration
// is a real confirmed FALSE, no matching ids, no concrete criterion
// evidence (design/configuration eligibility never admitted this design
// to the concrete funnel).
const FALSE_CONFIG = {
  configuration_id: "BD-1::baseline",
  boat_design_id: "BD-1",
  named_variant_id: null,
  truth: "FALSE" as const,
  criterion_evidence: [
    {
      criterion: { kind: "CATEGORICAL" as const, field: "power_drive_configuration", equals: "SHAFT" },
      field: "power_drive_configuration",
      truth: "FALSE" as const,
      reason: null,
      explanation: "design value OUTBOARD does not satisfy SHAFT",
      observed_value: "OUTBOARD",
    },
    {
      criterion: {
        kind: "NUMERIC" as const,
        field: "power_engine_count",
        comparison: "RANGE" as const,
        threshold_min: "2",
        threshold_max: "2",
      },
      field: "power_engine_count",
      truth: "TRUE" as const,
      reason: null,
      explanation: "design value 2 satisfies 2",
      observed_value: "2",
    },
  ],
};
const VALID_DESIGN_LINKED_NON_MATCH_VIEW: PowerSearchFitView = {
  ...VALID_DESIGN_LINKED_VIEW,
  result_class: "CONFIRMED_NON_MATCH",
  design_evaluation: {
    design_id: "BD-1",
    result_class: "CONFIRMED_NON_MATCH",
    matching_configuration_ids: [],
    reason: null,
  },
  design_configuration_evidence: [FALSE_CONFIG],
  criterion_evidence: [],
};

// A genuinely valid design-linked INSUFFICIENT_DATA: no configuration is
// TRUE, no matching ids, one configuration UNKNOWN (a legitimately
// incomplete configuration space).
const UNKNOWN_CONFIG = {
  configuration_id: "BD-1::baseline",
  boat_design_id: "BD-1",
  named_variant_id: null,
  truth: "UNKNOWN" as const,
  criterion_evidence: [
    {
      criterion: { kind: "CATEGORICAL" as const, field: "power_drive_configuration", equals: "SHAFT" },
      field: "power_drive_configuration",
      truth: "UNKNOWN" as const,
      reason: "VALUE_MISSING",
      explanation: "design drive type has no accepted mapping",
      observed_value: null,
    },
  ],
};
const VALID_DESIGN_LINKED_INSUFFICIENT_VIEW: PowerSearchFitView = {
  native_listing_id: "NL-1",
  domain: "POWER",
  active_requirement: { power_drive: "SHAFT" },
  result_class: "INSUFFICIENT_DATA",
  design_evaluation: {
    design_id: "BD-1",
    result_class: "INSUFFICIENT_DATA",
    matching_configuration_ids: [],
    reason: "CONFIGURATION_AMBIGUOUS",
  },
  design_configuration_evidence: [UNKNOWN_CONFIG],
  criterion_evidence: [],
  vessel_category_exclusion: null,
  source_basis: null,
  blockers: ["BOATDESIGN_CONFIGURATION_UNRESOLVED"],
};

test("fetchPowerSearchFit: valid claim-only shape is surfaced as ok", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, VALID_CLAIM_ONLY_VIEW),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.result_class, "CONFIRMED_MATCH");
        assert.equal(result.data.source_basis, "PUBLISHER_CLAIM");
        assert.equal(result.data.design_evaluation, null);
      }
    },
  );
});

test("fetchPowerSearchFit: valid design-linked combined shape is surfaced as ok", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, VALID_DESIGN_LINKED_VIEW),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.result_class, "CONFIRMED_MATCH");
        assert.equal(result.data.source_basis, null);
        assert.ok(result.data.design_evaluation !== null);
      }
    },
  );
});

test("fetchPowerSearchFit: valid design-linked two-configuration MATCH (both TRUE, both listed) is accepted", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, VALID_DESIGN_LINKED_TWO_CONFIG_MATCH_VIEW),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchPowerSearchFit: valid design-linked CONFIRMED_NON_MATCH (all configurations FALSE) is accepted", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, VALID_DESIGN_LINKED_NON_MATCH_VIEW),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.result_class, "CONFIRMED_NON_MATCH");
      }
    },
  );
});

test("fetchPowerSearchFit: valid design-linked INSUFFICIENT_DATA (no TRUE configuration) is accepted", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, VALID_DESIGN_LINKED_INSUFFICIENT_VIEW),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.result_class, "INSUFFICIENT_DATA");
      }
    },
  );
});

test("fetchPowerSearchFit: Finding F (a) CONFIRMED_NON_MATCH with a genuinely TRUE configuration is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_NON_MATCH_VIEW,
        design_configuration_evidence: [VALID_DESIGN_LINKED_VIEW.design_configuration_evidence[0]],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: Finding F (a) CONFIRMED_NON_MATCH with an UNKNOWN (never genuinely FALSE) configuration is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_NON_MATCH_VIEW,
        design_configuration_evidence: [UNKNOWN_CONFIG],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: Finding F (b) INSUFFICIENT_DATA with a genuinely TRUE configuration is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_INSUFFICIENT_VIEW,
        design_configuration_evidence: [VALID_DESIGN_LINKED_VIEW.design_configuration_evidence[0]],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: Finding F (b) INSUFFICIENT_DATA with a nonempty matching_configuration_ids is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_INSUFFICIENT_VIEW,
        design_evaluation: {
          ...VALID_DESIGN_LINKED_INSUFFICIENT_VIEW.design_evaluation!,
          matching_configuration_ids: ["BD-1::baseline"],
        },
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: Finding F (c) MATCH omitting a second genuine TRUE configuration from matching_configuration_ids is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_TWO_CONFIG_MATCH_VIEW,
        design_evaluation: {
          ...VALID_DESIGN_LINKED_TWO_CONFIG_MATCH_VIEW.design_evaluation!,
          matching_configuration_ids: ["BD-1::baseline"],
        },
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: Finding F (d) a configuration naming a different boat_design_id is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_VIEW,
        design_configuration_evidence: [
          { ...VALID_DESIGN_LINKED_VIEW.design_configuration_evidence[0], boat_design_id: "BD-OTHER" },
        ],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: Finding F (e) a duplicate configuration_id across design_configuration_evidence is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_TWO_CONFIG_MATCH_VIEW,
        design_configuration_evidence: [
          VALID_DESIGN_LINKED_VIEW.design_configuration_evidence[0],
          { ...SECOND_TRUE_CONFIG, configuration_id: "BD-1::baseline" },
        ],
        design_evaluation: {
          ...VALID_DESIGN_LINKED_TWO_CONFIG_MATCH_VIEW.design_evaluation!,
          matching_configuration_ids: ["BD-1::baseline", "BD-1::baseline"],
        },
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: Finding F (e) a duplicated matching_configuration_ids entry (even of a genuinely TRUE id) is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_VIEW,
        design_evaluation: {
          ...VALID_DESIGN_LINKED_VIEW.design_evaluation!,
          matching_configuration_ids: ["BD-1::baseline", "BD-1::baseline"],
        },
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: malformed (non-JSON) body degrades to service_error, never throws", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("not valid json {{{");
    },
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a well-formed but structurally wrong-shaped body is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { native_listing_id: "NL-1" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a body with domain != POWER is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { ...VALID_CLAIM_ONLY_VIEW, domain: "SAIL" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a response naming a different (cross-listing) native_listing_id is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { ...VALID_CLAIM_ONLY_VIEW, native_listing_id: "NL-OTHER" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: active_requirement echoing an extra unrequested key is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_CLAIM_ONLY_VIEW,
        active_requirement: { power_drive: "SHAFT", power_engine_count: "2" },
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: active_requirement missing the requested key is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { ...VALID_CLAIM_ONLY_VIEW, active_requirement: {} }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: active_requirement echoing a changed value is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, { ...VALID_CLAIM_ONLY_VIEW, active_requirement: { power_drive: "POD" } }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a combined request missing the count evidence leaf is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_VIEW,
        criterion_evidence: [VALID_DESIGN_LINKED_VIEW.criterion_evidence[0]],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a combined request with the drive leaf duplicated instead of count is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_VIEW,
        criterion_evidence: [
          VALID_DESIGN_LINKED_VIEW.criterion_evidence[0],
          VALID_DESIGN_LINKED_VIEW.criterion_evidence[0],
        ],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: an evidence leaf for an unrequested field (count leaf on a drive-only request) is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_CLAIM_ONLY_VIEW,
        criterion_evidence: [
          VALID_CLAIM_ONLY_VIEW.criterion_evidence[0],
          VALID_DESIGN_LINKED_VIEW.criterion_evidence[1],
        ],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: CONFIRMED_MATCH declared but design_evaluation present with source_basis also PUBLISHER_CLAIM is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_DESIGN_LINKED_VIEW,
        source_basis: "PUBLISHER_CLAIM",
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { powerDrive: "SHAFT", powerEngineCount: "2" },
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: claim-only view declared with source_basis null (no design_evaluation) is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { ...VALID_CLAIM_ONLY_VIEW, source_basis: null }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a CONFIRMED_NON_MATCH declared with a vessel_category_exclusion but nonempty criterion_evidence is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_CLAIM_ONLY_VIEW,
        result_class: "CONFIRMED_NON_MATCH",
        vessel_category_exclusion: { resolution: "SAIL", reason: "CONCRETE_ONLY" },
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: an unrecognized vessel_category_exclusion resolution (e.g. POWER) is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_CLAIM_ONLY_VIEW,
        result_class: "CONFIRMED_NON_MATCH",
        criterion_evidence: [],
        vessel_category_exclusion: { resolution: "POWER", reason: "CONCRETE_ONLY" },
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: an impossible TRUE aggregate (TRUE result_class with a FALSE leaf) is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_CLAIM_ONLY_VIEW,
        criterion_evidence: [
          {
            ...VALID_CLAIM_ONLY_VIEW.criterion_evidence[0],
            truth: "FALSE",
            observed_value: "POD",
          },
        ],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: result_class disagreeing with its own (all-TRUE) leaf aggregate is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { ...VALID_CLAIM_ONLY_VIEW, result_class: "INSUFFICIENT_DATA" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a FALSE leaf whose observed_value equals the requested value (self-contradiction) is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_CLAIM_ONLY_VIEW,
        result_class: "CONFIRMED_NON_MATCH",
        criterion_evidence: [
          { ...VALID_CLAIM_ONLY_VIEW.criterion_evidence[0], truth: "FALSE", observed_value: "SHAFT" },
        ],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: an unknown blocker token is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_CLAIM_ONLY_VIEW,
        result_class: "INSUFFICIENT_DATA",
        criterion_evidence: [
          { ...VALID_CLAIM_ONLY_VIEW.criterion_evidence[0], truth: "UNKNOWN", observed_value: null },
        ],
        blockers: ["SOMETHING_ELSE"],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a genuine INSUFFICIENT_DATA with the correct POWER_DRIVE_UNCONFIRMED blocker is accepted", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        ...VALID_CLAIM_ONLY_VIEW,
        result_class: "INSUFFICIENT_DATA",
        criterion_evidence: [
          { ...VALID_CLAIM_ONLY_VIEW.criterion_evidence[0], truth: "UNKNOWN", observed_value: null },
        ],
        blockers: ["POWER_DRIVE_UNCONFIRMED"],
      }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchPowerSearchFit: only the supplied scenario fields are forwarded as query params", async () => {
  await withServer(
    (req, res) => {
      const url = new URL(req.url ?? "", "http://localhost");
      assert.equal(url.searchParams.get("power_drive"), "SHAFT");
      assert.equal(url.searchParams.has("power_engine_count"), false);
      jsonResponse(res, 200, VALID_CLAIM_ONLY_VIEW);
    },
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchPowerSearchFit: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 401, { detail: "authentication required" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("fetchPowerSearchFit: 404 is surfaced as not_found (non-enumerating)", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 404, { detail: "organization not found" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("fetchPowerSearchFit: 403 mfa_required body is distinguished from publisher_role_required", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 403, { error: "mfa_required" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("fetchPowerSearchFit: 403 publishing_denied/PUBLISHER_ROLE_REQUIRED body is surfaced distinctly", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 403, { error: "publishing_denied", reason: "PUBLISHER_ROLE_REQUIRED" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "publisher_role_required");
    },
  );
});

test("fetchPowerSearchFit: 400 invalid_scenario carries the message", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 400, { error: "invalid_scenario", message: "bad value" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "invalid_scenario");
      if (result.kind === "invalid_scenario") {
        assert.equal(result.message, "bad value");
      }
    },
  );
});

test("fetchPowerSearchFit: 409 is not_previewable", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 409, { error: "not_previewable" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "not_previewable");
    },
  );
});

test("fetchPowerSearchFit: 503 is chain_integrity_fault", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 503, { error: "chain_integrity_fault" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "chain_integrity_fault");
    },
  );
});
