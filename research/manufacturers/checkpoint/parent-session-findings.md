# SLICE-0019 checkpoint — parent-session work product

Work produced directly in the orchestrating (parent) session, not by a subagent:

1. `research/manufacturers/registry_schema.json` — a strict, committed-in-working-tree
   JSON Schema (draft 2020-12) for the non-canonical manufacturer research registry.
   This file already exists in the working tree from before the checkpoint and is
   included in this checkpoint commit so it is not lost as an untracked file.
   It has not yet been used to validate a merged `registry.json` — that step was not
   reached before the usage-limit interruption.

2. Aggregate analysis of the 5 recovered batches (computed directly against the raw
   JSON files, no new research):
   - total raw records across recovered batches: 112
   - by disposition: 63 verified, 43 needs_review, 6 excluded
   - distinct countries observed: 18 (Austria, Belgium, Canada, Croatia, Czech Republic,
     Denmark, England, Finland, France, Germany, Netherlands, Norway, Poland, Slovenia,
     Sweden, United States, Wales, and one additional UK constituent country recorded
     by the UK/Ireland workstream)
   - macro-regions observed: North America, UK & Ireland, Western Europe, Eastern Europe, Nordics (5 of 8 target regions)
   - historical/defunct/acquired/renamed-status records: 55
   - records with an official_heritage_archive populated: 33

3. No `registry.json`, no `REPORT.md`, and no 20-entity source-yield study exist yet.
   These remain to be produced in a resumed session, per SLICE-0019's required outputs.

No new web research, browsing, or verification was performed while producing this
checkpoint. All figures above are recomputed directly from the already-recovered
raw JSON files.
