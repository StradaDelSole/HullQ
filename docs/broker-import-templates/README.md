# Broker inventory import templates — SLICE-0083

Canonical minimum example files for the multi-format broker inventory
import intake (`docs/slices/SLICE-0083-multiformat-broker-inventory-intake.md`),
referenced from the Broker Workspace upload page. These are examples, not
a fixed required schema -- any column layout works, since every column is
explicitly mapped (or ignored) by the broker after upload.

## Files

- `template.csv` -- comma-delimited, UTF-8, with a stable `Broker Ref`
  column suitable for the normal (non-snapshot) mapping mode.
- `template.tsv` -- identical content, tab-delimited.
- `template.json` -- identical content as the documented
  `{"listings": [...]}` JSON profile.
- `template_no_stable_id.csv` -- the same data with no stable per-row ID
  column at all, for the explicit one-time **snapshot mode** path.

Excel (`.xlsx`/`.xls`/`.xlsb`) and OpenDocument (`.ods`) files use the
identical column-per-row shape as the CSV template above, with an
explicit worksheet selection at upload time; no separate template file is
needed beyond "the same table, in a spreadsheet".

## Supported formats

| Format | Extension | Notes |
|---|---|---|
| CSV | `.csv` | UTF-8 (optional BOM); explicit comma or semicolon dialect selection at upload time -- never auto-detected |
| TSV | `.tsv` | UTF-8 (optional BOM); tab-delimited |
| Excel | `.xlsx`, `.xls`, `.xlsb` | Explicit worksheet selection required; macro-enabled content rejected |
| OpenDocument | `.ods` | Explicit worksheet selection required |
| JSON | `.json` | A top-level array of row objects, or `{"listings": [...]}` |
| NautiX 1.4 | `.xml` | `adverts.xml` validated against the pinned official XSD; no manual column mapping -- field semantics are fixed by the schema |

## Mapping targets

After upload, every detected column is assigned to exactly one of:

- `physical_boat.marketed_brand_claim`
- `physical_boat.model_designation_claim`
- `physical_boat.build_year` (a plain 4-digit year)
- `physical_boat.boat_name`
- `listing_offer.asking_price_mode` (`AMOUNT` or `POA`)
- `listing_offer.asking_price_amount` (a plain decimal, no currency symbol or thousands separator)
- `listing_offer.currency` (3-letter ISO code)
- `listing_offer.location_country` (2-letter ISO code)
- `listing_offer.location_region`
- `broker_listing_reference`
- `listing_offer.broker_description`
- the stable source-record-key column (dedup identity), **or**
- ignored

A blank cell always means "no claim for this field" -- it is never
guessed. A cell that cannot be coerced to its target's expected shape
(e.g. a price with a currency symbol) makes that row `INVALID` with an
explicit reason; it is never silently dropped or guessed.

## Stable ID vs. snapshot mode

If your source file has a genuinely stable per-row identifier (an order
number, internal reference, etc.), map that column as the source-record-
key. Re-uploading the same file is then always an exact, safe replay.

If your source file has **no** such column (`template_no_stable_id.csv`),
select **one-time snapshot mode** instead. Every row gets a server-
authored key derived from the exact uploaded file's own SHA-256 digest
plus its row position. Re-uploading the *exact same bytes* is still a
safe, idempotent replay. A **changed** file for the same import source
can never establish row continuity with an earlier snapshot upload -- it
is instead classified `CONFLICT_REVIEW` for every row, and never silently
creates a second batch of drafts for what might be the same boats.

## Per-row/per-file outcome vocabulary

- `VALID` / `INVALID` / `CONFLICT_REVIEW` -- the content/mapping-level
  preview classification, shown before you confirm.
- `CREATE_NEW_DRAFT` / `ALREADY_IMPORTED` / `CONFLICT_REVIEW` / `INVALID`
  -- the final per-row outcome after you explicitly confirm (D26).

Whole-file/whole-upload failures (`UNSUPPORTED_FORMAT`, `MALFORMED`,
`EMPTY`, `OVERSIZE`, `TOO_MANY_ROWS`, `TOO_MANY_COLUMNS`,
`DUPLICATE_HEADER`, `ENCRYPTED`, `WORKSHEET_REQUIRED`,
`WORKSHEET_NOT_FOUND`) are reported with an actionable message and create
nothing.

## NautiX 1.4

`adverts.xml` is validated against the pinned official v1.4 XSD before
any field is read. Only `advert type="boat" purpose="sale"` records
within HullQ's currently accepted sailboat types are mapped; every other
advert is explicitly `INVALID` with a reason, never silently skipped. A
`status="inactive"` advert is `CONFLICT_REVIEW`, never an automatic
withdrawal of anything already published. Fields outside the accepted
draft schema -- media image URLs/checksums, source subtitle text, and
every other NautiX field not listed under "Mapping targets" above --
remain visible as inert staged evidence in the row preview; none of them
is ever fetched over the network, and none becomes an accepted draft
fact. You must attest the exact NautiX account token(s) you own at
upload time; adverts under any other account token are `INVALID`.

## Source rights and retention

Only upload a file you are authorized to export/use -- this importer
never asserts a NautiX Nautic Network partnership or any other third-
party feed right on your behalf. An unconfirmed staged batch is retained
for 24 hours and then purged automatically; a confirmed batch's rows are
kept indefinitely as auditable import provenance alongside the private
drafts they produced.

## What this import never does

- Never creates a public listing, `NativeListing`, `PhysicalBoat` or
  `MarketEpisode` -- every confirmed row becomes an ordinary private
  `ProfessionalListingDraft`, editable in the existing drafts workspace.
- Never promotes or publishes anything, and never asserts a canonical
  `BoatDesign` association.
- Never executes a spreadsheet formula or macro, and never fetches a
  referenced media URL.
