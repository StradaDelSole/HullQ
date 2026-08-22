# SLICE-0019 research checkpoint

**Checkpoint timestamp (UTC):** 2026-08-22T14:12:37.356959+00:00
**Reason:** the orchestrating session's shared account-level usage limit was hit while
7 parallel regional research agents were active (WebSearch budget exhausted at
200/200 calls for the session; several subagents were terminated mid-task by an
upstream API error, "session limit · resets 4pm (Europe/Berlin)"). This checkpoint
preserves everything already obtained before any further research is attempted.

## Workstreams and recovery status

| # | Workstream | Scope | Status | Records | Checkpoint file |
|---|---|---|---|---|---|
| 1 | agent-01 | North America (USA, Canada) | **FULLY RECOVERED** | 34 (raw) | `checkpoint/agent-01-findings.md` + `checkpoint/raw/batch_a_north_america.json` |
| 2 | agent-02 | UK & Ireland | **FULLY RECOVERED** | 20 (raw) | `checkpoint/agent-02-findings.md` + `checkpoint/raw/batch_b_uk_ireland.json` |
| 3 | agent-03 | France, Belgium, Netherlands | **FULLY RECOVERED** | 24 (raw) | `checkpoint/agent-03-findings.md` + `checkpoint/raw/batch_c_france_benelux.json` |
| 4 | agent-04 | Germany/Austria/Switzerland + Poland/Slovenia/Croatia/Czech Republic | **FULLY RECOVERED** (this workstream completed normally, no crash) | 13 (raw) | `checkpoint/agent-04-findings.md` + `checkpoint/raw/batch_d_germanic_eastern_europe.json` |
| 5 | agent-05 | Sweden, Finland, Norway, Denmark | **FULLY RECOVERED** | 21 (raw) | `checkpoint/agent-05-findings.md` + `checkpoint/raw/batch_e_nordics.json` |
| 6 | agent-06 | Italy, Spain, Portugal, Greece, Malta | **PARTIALLY_RECOVERED** — one unverified process-commentary sentence survives in session state (no structured records; two bare unverified name leads "Belliure"/"Furia") | 0 structured | `checkpoint/agent-06-findings.md` |
| 7 | agent-07 | Taiwan, China, Hong Kong, Japan, Australia, New Zealand, South Africa, Brazil, Argentina, Turkey | **UNAVAILABLE** — the failure notification carried no result text at all; nothing survives in session state | 0 | `checkpoint/agent-07-findings.md` |

Recovery method for workstreams 6 and 7: the orchestrating session inspected its own
already-received task-completion notifications for these two agents (the only
"resumed session state" available for a terminated background agent). No raw
subagent transcript was opened, no new tool call was issued against the web, and no
new agent was launched. Workstreams 1-5 required no such recovery step: their output
files were already present and valid on disk.

Parent-session (non-subagent) work product recovered in `checkpoint/parent-session-findings.md`
and the pre-existing `research/manufacturers/registry_schema.json`.

## Aggregate state of recovered material (raw, pre-merge, pre-dedupe)

- total raw records recovered: **112**
- disposition: **63 verified / 43 needs_review / 6 excluded**
- distinct countries observed: **18**
- macro-regions observed: **5 of 8** (North America, UK & Ireland, Western Europe, Eastern Europe, Nordics)
- historical/defunct/acquired/renamed-status records: **55**
- records with an official heritage/model-archive source: **33**

These are raw counts before deduplication, ID assignment, or final review adjudication —
they are NOT yet the finished SLICE-0019 registry.

## Known gaps as of this checkpoint

- Southern Europe (Italy/Spain/Portugal/Greece/Malta) has **zero** recovered records —
  a real `coverage_gap`, not yet filled.
- Asia-Pacific and Rest of World (Taiwan/China/Hong Kong/Japan/Australia/New
  Zealand/South Africa/Brazil/Argentina/Turkey) has **zero** recovered records —
  a real `coverage_gap`, not yet filled.
- Against the SLICE-0019 floors: the >=40 historical, >=25 heritage-archive, and
  >=5-macro-region floors already appear met from recovered data alone; the
  >=120 verified-eligible-record floor and the >=20-country floor are NOT yet
  met (112 raw / 106 non-excluded recovered so far; 18 countries so far) and
  require either resuming the two lost workstreams or otherwise closing the gap
  in a later session.
- `registry.json`, `REPORT.md`, and the 20-entity source-yield study have **not**
  been produced yet.
- No overlap cross-check against the accepted SLICE-0017/0018 Wikidata universe
  has been performed yet.
- No canonical HullQ entity was created or modified. No SailboatData value was
  used. No subjective bluewater/offshore/luxury classification was introduced.

## Exactly what must be resumed later

1. Re-run (or otherwise complete) the Southern Europe and Asia-Pacific/Rest-of-World
   research workstreams once the session/account usage limit has reset, OR accept
   the gap and report it explicitly in the final REPORT.md as an unmet floor.
2. Merge the 5 recovered batches (plus any newly completed ones) into
   `research/manufacturers/registry.json`, assigning stable `RSRCH-MFR-NNNN` IDs,
   validating against the already-committed `registry_schema.json`.
3. Select and execute the 20-entity source-yield study.
4. Perform the exact/unambiguous overlap cross-check against
   `research/bootstrap/wikidata/manifest.json` and `sl0018-2500/manifest.json`.
5. Write `research/manufacturers/REPORT.md` per the SLICE-0019 required sections.
6. Run repository validation, commit, and push the finished slice deliverable,
   leaving SLICE-0019 in `REVIEW` or `BLOCKED` as appropriate.

No new web research, browsing, agent launches, or verification were performed in
producing this checkpoint. This checkpoint is preservation-only.
