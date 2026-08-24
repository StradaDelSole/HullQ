# SLICE-0021 — Acceptance Closure

**ID:** SLICE-0021  
**Final status:** DONE  
**Owner accepted:** 2026-08-24  
**Independent-review verdict:** ACCEPT  
**Implementation/research PR:** #50 — "SLICE-0021: alternative Wikidata sailboat-class discovery-semantics pilot"  
**Final reviewed / accepted implementation-research head:** `2cf0ab437d2347a574fd5a01b3e5577ca4c6b521`  
**Implementation/research merge commit:** `c562b1c8f082f60823e084b1fb24c9f5c6f6ba00`  
**Exact-head CI:** GitHub Actions run #260, run ID `32759454547`, conclusion **SUCCESS**

## Acceptance result

SLICE-0021 is explicitly accepted by the project owner and closed as `DONE`.

The slice performed one bounded, rights-gated Wikidata structured-data discovery measurement over exactly four precommitted query routes. It measured alternative sailboat-class discovery semantics beyond the accepted direct-`P31` definition without changing HullQ's production discovery rule or canonical identity universe.

Exact-head CI on the final accepted head (`2cf0ab437d2347a574fd5a01b3e5577ca4c6b521`) — run #260 / ID `32759454547` — passed with all jobs `SUCCESS`: quality (ubuntu-latest), quality (windows-latest), db integration (PostgreSQL 18), dependency audit. The PostgreSQL job also validated the retained SLICE-0021 schemas and ran the hardened offline `--verify` path successfully.

## Final retained measurement

The accepted retained result is:

```text
R0 current direct control                    1,829
R0 drift vs retained direct universe             0

R1 sailboat-class P31/P279* closure          1,882
R1 incremental vs current R0                    53

R2 legacy sailboat-class closure                 0
R2 incremental vs current R0                     0

R3 structured repair signal                      4
R3 incremental vs current R0                     4

alternative-route union                         57
R1 ∩ R2                                           0
R1 ∩ R3                                           0
R2 ∩ R3                                           0
```

The accepted historical comparison boundaries remain unchanged:

- retained direct-discovery universe: **1,829 QIDs**;
- accepted AUTO_ADMIT BoatModel universe: **1,770 identities**;
- SLICE-0017 manifest SHA256: `076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845`;
- SLICE-0018 manifest SHA256: `41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f`.

R0 reproduced the retained 1,829-QID direct universe with zero drift: 1,829 still present, zero absent, zero new direct-instance QIDs since the retained SLICE-0018 measurement.

## Sample / identity-signal result

All **57** incremental alternative-route QIDs were selected by the deterministic bounded entity-detail sampler, remaining below both the <=75-per-route and <=200-global caps. Entity-detail acquisition completed 57/57 through `wbgetentities`.

Exact-only identity-signal categories against the accepted 1,770 universe were:

- `accepted_qid_overlap`: **0**;
- `exact_identity_signal_other_qid`: **0**;
- `no_exact_identity_signal`: **57**;
- `unresolved_exact_identity_signal`: **0**.

`no_exact_identity_signal` retains only its narrow accepted meaning: the bounded exact QID/label/alias probe found no exact signal. It does not prove global novelty, prove the absence of a corresponding HullQ identity, or authorize canonical admission.

Matching remained exact-only: QID first, then case-insensitive label/retained-alias comparison with surrounding-whitespace trimming only. No internal-whitespace collapse, punctuation rewriting, manufacturer-prefix manipulation, token reordering, fuzzy matching, generation collapsing or semantic identity inference was used.

## Route dispositions

The accepted evidence-derived dispositions are:

- R1: `FOLLOWUP_DISCOVERY_CANDIDATE`;
- R2: `NO_INCREMENTAL_YIELD`;
- R3: `FOLLOWUP_DISCOVERY_CANDIDATE`.

These are recommendation-only research dispositions, not production authorization.

R3 remains explicitly repair/review-bound. Its four retained candidates include Lagoon 380, Lagoon 500, Lagoon 560 and Beneteau Evasion 25, each surfaced because its structured English description contains "sailboat class" while the retained item is modeled as an instance of generic `sailboat` (`Q1075310`). R3 membership does not prove correct HullQ BoatModel identity or authorize a production classification rule.

## Retained package and reproducibility

Accepted retained artifacts remain under:

`research/bootstrap/wikidata/sl0021-alt-discovery/`

including:

- `discovery_probe_schema.json`;
- `discovery_probe.json`;
- `sampled_candidates_schema.json`;
- `sampled_candidates.json`;
- `REPORT.md`.

Normal CI performs no live Wikidata acquisition. The retained measurement can be revalidated offline with `scripts/bootstrap/wikidata_sl0021_alt_discovery_runner.py --verify`.

The final accepted implementation fails closed on incomplete live entity-detail sample coverage and independently recomputes/validates route definitions and digests, immutable input references, direct drift, incremental QID sets, pairwise/union/unique-contribution overlap sets, deterministic sample selection, candidate membership, identity-signal categories, category totals, accepted-universe references and route dispositions.

## Amendment / review history

1. Initial implementation produced the one retained live Wikidata measurement and placed the slice in `REVIEW`.
2. **Independent review round 1 → AMEND.** The measured result itself was provisionally accepted, but offline verification did not independently recompute every structurally derivable retained field and the committed completion report created a self-referential exact-head CI provenance problem.
3. Round-1 amendment head `b2b22706bb0d74a8c311d45776fa7f6c5c31bc72` added fail-closed live sample-completeness checking, route-record/immutable-input/sample self-consistency verification and tamper-detection tests, while removing the false current-head CI characterization. The retained live measurement was not rerun or changed.
4. **Independent review round 2 → AMEND.** The round-1 fixes were accepted, with one remaining narrow audit gap: several retained derived QID lists/sets were still validated only through counts.
5. Round-2 amendment head `2cf0ab437d2347a574fd5a01b3e5577ca4c6b521` added exact full-set validation for drift QID lists, R1/R2/R3 incremental QIDs, all pairwise overlap sets, total union, unique contributions and the sampled-candidate accepted-universe reference. Seventeen additional tamper tests were added. The retained live measurement and report artifacts remained byte-unchanged.
6. **Final independent review → ACCEPT.** No unresolved findings remained.
7. Exact-head CI #260 / `32759454547` on the final accepted head passed all four jobs.
8. PR #50 was merged to `main` as `c562b1c8f082f60823e084b1fb24c9f5c6f6ba00`.
9. The project owner explicitly accepted SLICE-0021 on 2026-08-24.

## No production/canonical scope crossed

- no canonical Brand/Organization/BoatModel/BoatDesign row was created, modified or deleted;
- no HullQ ID was minted for any alternative-route candidate;
- no accepted SLICE-0017/0018 manifest or retained crosswalk was modified;
- no production Wikidata discovery query was changed;
- R1/R2/R3 were not promoted into production discovery behavior;
- no manufacturer archive, Wikipedia, PetScan, DBpedia or SailboatData acquisition was introduced;
- no broad technical enrichment was performed;
- no SLICE-0022 was created or started.

## Evidence trail

- implementation/research PR: #50;
- final reviewed / accepted implementation head: `2cf0ab437d2347a574fd5a01b3e5577ca4c6b521`;
- exact-head CI: GitHub Actions run #260, ID `32759454547`, conclusion **SUCCESS**;
- independent-review final verdict: **ACCEPT**;
- implementation/research merge commit: `c562b1c8f082f60823e084b1fb24c9f5c6f6ba00`;
- project-owner acceptance: 2026-08-24.

## Next boundary

No SLICE-0022 or later slice is made `READY` by this closure.

The 53 R1 incremental QIDs and four R3 repair signals justify considering a later bounded Stage-3 follow-up, but this closure does not authorize automatic canonical admission, production adoption of alternative Wikidata discovery routes, manufacturer-archive ingestion, a new external source, review-queue resolution, broad Tier-1/Tier-2 enrichment, query-engine/API/frontend work, marketplace integration, accounts/alerts/monitoring or price-history work.

Any next slice requires its own bounded readiness contract, explicit acceptance criteria and the normal `START_SLICE.bat` workflow. No later slice begins automatically.
