# SLICE-0019 manufacturer review batch 002 — delta-first North America / UK

**Scope:** bounded independent review of 8 recovered `needs_review` records.

**Method:** strict evidence-delta review. For each record the already-preserved Claude evidence set was inspected first. No web research was performed where the retained evidence already supported an adjudication with uncertainty preserved. Additional web research was used only for a concrete unresolved factual/identity question.

**Additional web checks in this batch:**

1. Islander Yachts — exact historical lineage / closure narrative.
2. Marine Projects (Plymouth) Ltd — legal/company continuity and later name.
3. Bowman/Rustler current-site spot check — whether the current Rustler surface actually substantiates the recovered claim that Bowman is still actively offered.

No `registry.json` or canonical HullQ entity is modified by this note.

## 1. Islander Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical series-sailboat manufacturer, but correct the recovered closure narrative.

- The recovered Claude record already had consistent specialist evidence for Islander as a real production builder and for substantial model output.
- A targeted owner-association historical archive provides detailed first-hand/near-first-hand company recollections and factory-production history, including the Islander 36 production run and corporate lineage through McGlasson / Wayfarer / Islander.
- This strengthens manufacturer eligibility sufficiently for `verified` research status.
- However, the recovered statement that production moved to Costa Rica and that the company went bankrupt in 1986 is too strong. The historical archive explicitly states that Islander production was last in Irvine, California; a possible Cabo Rico/Costa Rica asset transaction was discussed but was not consummated; and it disputes the claim that Islander filed Chapter 11 before closure.
- Recommended production-era handling: retain an estimated early-1960s start and circa-1986 end, but do not encode a Costa Rica production transfer or bankruptcy as fact without stronger evidence.

Existing preserved sources remain useful, plus:
- https://www.islander36.org/history-4a.html

## 2. Moody

**Provisional decision:** `PROMOTE TO VERIFIED` as **brand relationship context**, not as a manufacturer/yard-floor record.

- The retained official Moody history and Darglow history already establish the 1973 partnership with Marine Projects (Plymouth) Ltd, the 39-model / roughly 4,233-boat production run, the end of the family/Marine Projects era, and later acquisition by HanseYachts.
- The recovered `entity_kind=[brand]` is therefore materially correct and useful for HullQ relationship mapping.
- Because SLICE-0019's numeric floor is specifically for verified eligible **manufacturer/yard** records, Moody as a brand-only record MUST NOT count toward that floor.
- Recommended current-status handling: use `active` for the currently marketed Moody brand, with ownership/acquisition represented in explicit relationships. Do not use `acquired` as a substitute for current operational state if the brand is still active.

Preserved sources are sufficient; no new web research was required for the adjudication.

## 3. Marine Projects (Plymouth) Ltd

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical series-sailboat manufacturer/yard role, with a major identity correction: the principal Marine Projects company was renamed into the Princess Yachts lineage.

- The preserved Moody evidence already establishes Marine Projects as the actual production manufacturer for the long-running Moody GRP series and therefore satisfies series-sailboat manufacturer/yard eligibility.
- A targeted identity check resolves the recovered `status=unknown` problem.
- Princess Yachts' own corporate history states that the company was founded as **Marine Projects (Plymouth) Ltd** and that, with the Princess name established, **Marine Projects became Princess Yachts International in 2001**.
- UK Companies House confirms company no. **00856633**, incorporated 12 August 1965, with the previous name `MARINE PROJECTS (PLYMOUTH) LIMITED` until 2 August 2001 and subsequent Princess names. The same legal company is active today as Princess Yachts Limited.
- Therefore Marine Projects must not be modeled as a mysterious defunct/disappeared yard. The correct relationship is a rename/continuity into Princess Yachts.
- The series-sailboat role remains historical: Moody sailboat production began in 1973; the Moody partnership continued into the mid-2000s, spanning the 2001 corporate rename. The legal-name period and sailboat-production period must not be conflated.
- Beware a separate dormant company currently named `MARINE PROJECTS (PLYMOUTH) LIMITED` (company no. 00458049) whose historical names show it is not the 1965 Princess predecessor. Do not identity-merge it.

New authoritative sources:
- https://www.princessyachts.com/our-story/
- https://find-and-update.company-information.service.gov.uk/company/00856633

Existing Moody source:
- https://moody-yachts.com/us/history/

## 4. Sadler Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical/defunct series-sailboat manufacturer with chronology uncertainty retained.

- The preserved Darglow and Practical Boat Owner material already establishes a real production yard, the Sadler model family, Martin Sadler's manufacturing role, and substantial series output such as the Sadler 34 run.
- The unresolved exact company founding year does not prevent verification of manufacturer eligibility.
- Keep `start_year=null` (or later an explicitly estimated value only if directly supported) rather than inventing a year.
- Keep the end-of-production date around 1995 as `estimated` unless a stronger closure source is later found.
- Unknown chronology is preferable to leaving an otherwise well-supported manufacturer in `needs_review` solely because an exact start date is unavailable.

Preserved sources are sufficient; no new web research was required.

## 5. Rustler Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as an active manufacturer/yard, with corporate-continuity nuance preserved.

- Claude already retained an official current Rustler source plus Companies House evidence for the active `RUSTLER YACHTS LIMITED` legal entity.
- The official site clearly describes current in-house hand-building in Falmouth and exposes a current sailboat range.
- The discrepancy between a trading/manufacturing lineage beginning in the early/mid-1980s and the current legal company's 2000 incorporation does not undermine manufacturer eligibility; it means the record must not describe the 1985-to-present corporate identity as an exact uninterrupted legal entity without evidence.
- Recommended: verified active manufacturer/yard; preserve the earlier Rustler manufacturing lineage as historical/trading continuity and the 2000 legal-entity incorporation explicitly in ambiguity notes.

Preserved official/Companies House evidence is sufficient. Current official surface also confirms active manufacturing:
- https://www.rustleryachts.com/
- https://www.rustleryachts.com/about-rustler/

## 6. Bowman Yachts

**Provisional decision:** `KEEP / VERIFY ONLY AS BRAND RELATIONSHIP CONTEXT`; do **not** count toward the manufacturer/yard floor, and correct the recovered `status=active` unless current production is independently substantiated.

- The retained evidence establishes Bowman as a real sailboat brand, its merger with Rival, the Rival Bowman receivership, and acquisition by Rustler.
- This makes Bowman materially useful as brand/relationship context under SLICE-0019.
- The recovered record is already `entity_kind=[brand]`; therefore it is not itself a manufacturer/yard-floor record.
- A targeted check of Rustler's current official 2026 website found the active Rustler range but no current Bowman models on the surfaced range. That does not prove Bowman is dead, but it means the recovered assertion that Bowman is `active` and "continues today" is not sufficiently supported by the current official surface checked.
- Recommended current `status=unknown` unless a specific current Rustler/Bowman production source is later found.
- Research status may be `verified` for the historical brand/relationship facts once the unsupported active-status claim is removed; it must remain excluded from the >=120 manufacturer/yard floor count.

Relevant retained sources:
- https://www.darglow.co.uk/bowman-yachts/
- recovered Bowman/Rival relationship evidence

Current Rustler spot-check:
- https://www.rustleryachts.com/

## 7. Northshore Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical/defunct manufacturer/yard, retaining an estimated/uncertain founding lineage.

- The preserved Southerly and Vancouver histories independently establish Northshore's physical production role at Havant/Itchenor and its construction of the Southerly and Vancouver series.
- The inconsistent accounts of whether the 1971 origin is best described as Fairways Marine, Brian Moffat's yards, or the creation of a company called Northshore Yachts are an identity/chronology nuance, not evidence against the yard's existence or series-production eligibility.
- Recommended: verified manufacturer/yard; `start_year=1971` only with `basis=estimated`; `end_year=2014` may remain estimated for the relevant sailboat-production activity.
- Do not silently equate every predecessor/trading name; preserve Fairways/Northshore lineage in relationships/ambiguity notes.

Preserved sources are sufficient; no new web research was required.

## 8. Southerly

**Provisional decision:** `PROMOTE TO VERIFIED` as **brand relationship context** with `status=unknown`; do not count toward the manufacturer/yard floor.

- The retained sources already establish the Southerly production brand, its long manufacturing relationship with Northshore, the 2017 acquisition of the brand/tooling by Discovery Yacht Group, and the later closure of Discovery Shipyard in 2021.
- The post-2021/current producer is genuinely unresolved in the preserved evidence. This uncertainty should remain explicit rather than blocking verification of the well-supported historical brand relationships.
- Because the record is `entity_kind=[brand]`, it is relevant context but MUST NOT count toward the >=120 verified manufacturer/yard floor.
- Recommended: retain `status=unknown`, verified historical/relationship facts, and avoid asserting that a newly incorporated company with a similar Discovery name is the same producer without explicit evidence.

Preserved sources are sufficient; no new web research was required.

## Batch outcome

Of 8 reviewed records:

### Verified manufacturer/yard-floor candidates after correction

- **Islander Yachts** — verified historical manufacturer; closure narrative corrected.
- **Marine Projects (Plymouth) Ltd** — verified manufacturer/yard role; identity resolved into the Princess Yachts legal lineage.
- **Sadler Yachts** — verified historical manufacturer with unknown/estimated chronology retained.
- **Rustler Yachts** — verified active manufacturer/yard with legal-continuity nuance.
- **Northshore Yachts** — verified historical manufacturer/yard with estimated founding lineage.

### Verified relationship-context records, NOT manufacturer/yard-floor candidates

- **Moody** — verified brand context; active brand under later ownership; do not count toward floor.
- **Southerly** — verified brand context with current producer/status unknown; do not count toward floor.

### Relationship context still requiring current-status correction

- **Bowman Yachts** — historical brand/relationship facts are supported, but the recovered `active` claim is not substantiated by the current Rustler surface checked. Use `status=unknown` unless a specific current-production source is later found; do not count toward manufacturer/yard floor.

## Research-efficiency note

This batch demonstrates the intended post-checkpoint workflow: most adjudications required **zero new web research** because Claude's preserved sources already contained enough evidence once unknowns were allowed to remain unknown. New web work was limited to specific deltas that could materially change identity/status modeling. Future batches should follow the same rule.

No registry counts should be mechanically changed from this note alone. Final application to `registry.json`, stable research IDs, deduplication and report totals remain deferred until bounded research review is complete.