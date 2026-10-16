# SLICE-0088 — XLSB export writer feasibility blocker (2026-10-16)

**Status:** Feasibility stop recorded, pending Owner scope-amendment decision. No implementation code written for SLICE-0088. The slice contract (`docs/slices/SLICE-0088-broker-inventory-portability-export.md`) is unmodified; its declared eight-format target and acceptance criteria remain as written until the Owner explicitly accepts an amendment.

## What was checked

SLICE-0088's own stop conditions and mechanical-invariants section require establishing audited, CI-supported writer feasibility for XLS/XLSB/ODS *before* any writer is claimed as supported ("do not treat an experimental package or extension rename as proof"). This record is that executable feasibility check for XLSB specifically, run against this repository's pinned toolchain (`requires-python = ">=3.14,<3.15"`, `uv` dependency resolution).

## Reproducible evidence

1. `uv add --group dev pyxlsb odfpy` (run from the repository root, branch `slice/0088-broker-inventory-portability-export`) resolved and installed both packages cleanly under CPython 3.14.7: `pyxlsb==1.0.10`, `odfpy==1.4.1`. (This experiment was reverted via `git checkout -- pyproject.toml uv.lock`; the branch carries no dependency change.)
2. `uv run python -c "import pyxlsb; print([n for n in dir(pyxlsb) if not n.startswith('_')])"` printed:
   ```
   ['BIFF12Reader', 'Handler', 'Workbook', 'Worksheet', 'biff12', 'convert_date', 'handlers', 'open_workbook', 'reader', 'stringtable', 'workbook', 'worksheet']
   ```
   `pyxlsb` — the only established Python XLSB library — exposes a reader only (`open_workbook`, `Workbook`, `Worksheet`, `BIFF12Reader`). No writer class or write API exists in this package at this version, confirming the existing SLICE-0088 reconciliation note that "`python-calamine` is a **reader**, not a writer" applies identically to `pyxlsb` for XLSB.
3. Web search for a pure-Python XLSB writer surfaced one candidate, `xlspy` (PyPI, v0.4.1). It was not adopted or installed: version 0.4.x, a single apparent maintainer, and conflicting maintainer/repository attribution across sources (one result names `englandkaka/xlspy` on GitHub, another names `KrzysztofDusko/xlspy`) are exactly the "experimental package" profile the slice explicitly forbids treating as proof, and fail the slice's required "license, vulnerability and supply-chain scrutiny" bar for a new writer dependency touching real broker inventory data.
4. A further search identified **Aspose.Cells for Python via .NET** as an established commercial library with genuine XLSB write support. This confirms XLSB writing is not technically impossible in general, but:
   - it requires a commercial license (no purchase authorized here);
   - its CPython 3.14 compatibility, Linux/Windows deployment requirements (a .NET runtime dependency alongside HullQ's pinned CPython/FastAPI/VPS baseline) and supply-chain implications have not been evaluated or accepted for HullQ;
   - a genuine reimport-roundtrip proof against this library has not been run.
   No commercial dependency decision is made or implied by this record.

## Conclusion

The finding is not that an XLSB writer is impossible or unavailable anywhere — Aspose.Cells for Python via .NET demonstrates genuine XLSB write capability exists commercially. The finding is narrower: **no sufficiently vetted and Owner-approved XLSB writer has been established for HullQ** against its pinned CPython 3.14 / Ubuntu+Windows CI baseline. The one open-source candidate found (`xlspy`) fails the slice's own required license/vulnerability/supply-chain scrutiny bar, and the one viable candidate with a genuine track record (Aspose.Cells) requires a commercial license, a .NET runtime alongside HullQ's pinned CPython/VPS stack, and compatibility/roundtrip proof — none of which has been evaluated or accepted. This trips SLICE-0088's own stop condition: *"An accepted target writer cannot safely produce/re-import genuine XLS/XLSB/ODS on CI-supported OS/Python... report BLOCKED, actual feasibility evidence and proposed minimum scope amendment for explicit Owner approval."*

By contrast, for the same CI baseline:
- **XLS**: `xlwt` (already a dev dependency, `xlwt==1.3.0`) is a genuine legacy-XLS writer.
- **ODS**: `odfpy` resolves/installs cleanly and is a genuine ODS writer.
- **XLSX**: `xlsxwriter` (already a dev dependency, `xlsxwriter==3.2.9`) is a genuine XLSX writer.
- **CSV/TSV/JSON**: stdlib-sufficient.
- **NautiX 1.4 `adverts.xml`**: the existing pinned XSD and `lxml` (already a runtime dependency) support a validated writer direction, mirroring the accepted SLICE-0083 reader.

Those seven families have no equivalent feasibility blocker recorded here.

## Proposed minimum scope amendment (pending Owner approval)

1. Deliver the seven proven export families under SLICE-0088: CSV, TSV, XLSX, XLS, ODS, structured JSON, NautiX 1.4 `adverts.xml`.
2. Track XLSB export as a separately registered, explicitly deferred capability (not silently dropped, not implemented via an unvetted dependency) — to be revisited only if/when a production-safe open-source writer emerges or a commercial-dependency decision (e.g. Aspose.Cells) is separately proposed, licensed and accepted.
3. XLSB **import** is unaffected: the existing SLICE-0083 `python-calamine`-based reader keeps working unchanged; this blocker concerns only the new outbound writer direction SLICE-0088 would add.
4. No change to the slice's acceptance-criteria text, "all eight formats" objective language, `REQ-BROKER-022`/`MVP-BROKER-009` status, or DONE state until the Owner records explicit approval of this amendment (or a different resolution).

## Current slice state

- SLICE-0088 implementation: **not started** (no domain/application/persistence/API/web/test code changed).
- Branch `slice/0088-broker-inventory-portability-export`: carries only this documentation-only handoff plus the matching `BLOCKED` status/handoff marker on the primary slice document; no production code, tests, requirement completion markers or acceptance criteria were touched.
- Recommended slice status: `BLOCKED` (feasibility stop, not a design/requirements conflict) pending Owner decision on the proposed amendment above.
- Project Owner has agreed in principle with the seven-format amendment direction; this record and the primary-document handoff marker are the documented basis for the independent reviewer to examine before implementation resumes.

## Pending reconciliation on resume

This branch was created before `origin/main` commit `7927ab7` ("docs: enforce pre-pilot broker upload runtime STOP in controlling gates", merged via PR #361, docs-only: `docs/POST_SLICE_0087_EXTERNAL_CODE_REVIEW_RECONCILIATION_2026-10-16.md`, `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`, `docs/governance/PRODUCTION_READINESS_GATE.md`). That commit's own message records it as preserving accepted SLICE-0087 and READY SLICE-0088 state, so no immediate conflict is known, but this branch has not been rebased/merged onto it. Whoever resumes SLICE-0088 implementation must first reconcile against the then-current `origin/main` controlling gates (including PR #361's pre-pilot broker-upload runtime STOP) rather than resuming from this branch's older base unexamined.
