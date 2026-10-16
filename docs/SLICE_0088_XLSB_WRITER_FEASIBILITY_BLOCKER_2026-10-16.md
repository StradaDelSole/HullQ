# SLICE-0088 — XLSB export writer feasibility blocker (2026-10-16)

**Status:** Feasibility stop recorded and resolved. The Project Owner has **explicitly ACCEPTED** the seven-format scope amendment proposed below. No implementation code has been written for SLICE-0088 yet; the primary slice contract (`docs/slices/SLICE-0088-broker-inventory-portability-export.md`) has been amended accordingly (Status `REVIEW`, matching handoff marker) and now carries the seven-format target as its controlling scope, with the original eight-format decision preserved there as history. This record itself remains the evidence basis for that amendment and is unchanged below except for this status update and the tracking link.

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

## Owner-accepted scope amendment (2026-10-16) — ACCEPTED

1. SLICE-0088 delivers the seven proven export families: CSV, TSV, XLSX, XLS, ODS, structured JSON, NautiX 1.4 `adverts.xml`.
2. XLSB export is a separately registered, explicitly deferred capability (not silently dropped, not implemented via an unvetted or commercial dependency without separate authorization) — durably tracked in **[GitHub issue #362](https://github.com/StradaDelSole/HullQ/issues/362)**: a later investigation and possible development of a genuine XLSB export alternative, preferably without expensive commercial licensing. Any paid/commercial solution (e.g. Aspose.Cells) requires separate explicit Owner authorization before adoption.
3. XLSB **import** is unaffected: the existing SLICE-0083 `python-calamine`-based reader keeps working unchanged; this amendment concerns only the new outbound writer direction SLICE-0088 adds.
4. The primary slice contract's acceptance-criteria text, objective, in-scope formats and deliverables have been updated to the seven-format target (`docs/slices/SLICE-0088-broker-inventory-portability-export.md`, "Owner-accepted scope amendment (2026-10-16)" section); the original eight-format decision and this blocker's history are preserved there, not deleted. `REQ-BROKER-022`/`MVP-BROKER-009` status and DONE state are unaffected by this documentation-only amendment — those still require actual seven-format implementation, independent review and explicit Owner acceptance.

## Current slice state

- SLICE-0088 implementation: **not started** (no domain/application/persistence/API/web/test code changed by this or the prior documentation-only commit).
- Branch `slice/0088-broker-inventory-portability-export`: carries this feasibility record, the primary-document seven-format amendment, and is merged up to date with `origin/main` (including PR #361, see below). No production code, tests, requirement completion markers or acceptance-criteria checkboxes have been touched.
- Primary slice document status: `REVIEW` with matching `Status set by this handoff: REVIEW` marker — this documentation-only amendment is handed off for independent review before implementation resumes.
- Writer feasibility is not equivalent to acceptance proof: every one of the seven delivered formats must still pass genuine format and reimport tests when implementation proceeds; new runtime writer dependencies (`xlwt`, `xlsxwriter`, `odfpy`) must be declared as pinned main `[project.dependencies]`, not left in the dev-only group they currently occupy.

## Pending reconciliation on resume

This branch was created before `origin/main` commit `7927ab7` ("docs: enforce pre-pilot broker upload runtime STOP in controlling gates", merged via PR #361, docs-only: `docs/POST_SLICE_0087_EXTERNAL_CODE_REVIEW_RECONCILIATION_2026-10-16.md`, `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`, `docs/governance/PRODUCTION_READINESS_GATE.md`). That commit's own message records it as preserving accepted SLICE-0087 and READY SLICE-0088 state, so no immediate conflict is known, but this branch has not been rebased/merged onto it. Whoever resumes SLICE-0088 implementation must first reconcile against the then-current `origin/main` controlling gates (including PR #361's pre-pilot broker-upload runtime STOP) rather than resuming from this branch's older base unexamined.
