# Pinned genuine spreadsheet test fixtures — SLICE-0083 review amendment (item D)

## `calamine_date.xlsb`

A genuine binary Excel (XLSB/BIFF12) file -- not synthesized by this
repository's own code -- so `hullq.domain.import_spreadsheet.
parse_spreadsheet_table`/`list_spreadsheet_worksheets` are proven against
real third-party-authored XLSB bytes, not only against files our own
`xlsxwriter`-based test helper wrote.

**Source:** `tests/date.xlsb` from the `python-calamine`/`calamine` Rust
library's own upstream test corpus
(`https://github.com/tafia/calamine`) -- the exact Rust crate
`python-calamine` binds to read every spreadsheet format in this slice.
Using calamine's own test fixture means this file is already a file the
library's authors use to prove their XLSB reader correct.

**Retrieved:** 2026-10-12, via a direct HTTPS GET of
`https://raw.githubusercontent.com/tafia/calamine/master/tests/date.xlsb`.

**License:** `tafia/calamine` is MIT-licensed
(confirmed via the GitHub repository API `license.spdx_id: "MIT"` at
retrieval time) -- permissive reuse of its test fixtures is covered.

**Pinned SHA-256:**

```
68d36adf4d4de3890209e786eeb89a98778d25158628f83e96587e652fbb4eca
```

**Known content** (verified via `CalamineWorkbook` at pin time): one
worksheet `Sheet1`, 3 rows, 2 columns; column A alternates `date`/
`timedelta`-typed cells, column B is `float`. Tests that load this file
assert against this exact known shape rather than treating it as an
opaque blob.

**Reproduce the pin:**

```
curl -fsSL -o calamine_date.xlsb https://raw.githubusercontent.com/tafia/calamine/master/tests/date.xlsb
sha256sum calamine_date.xlsb
```

## `calamine_date.ods`

The identical-provenance companion to `calamine_date.xlsb` for
OpenDocument: a hand-authored minimal ODS zip was attempted first and
rejected by calamine's own format sniffing (`Cannot detect file format`)
-- rather than spend further effort debugging a synthetic container
against an undocumented sniffer heuristic, this uses calamine's own real
`tests/date.ods` fixture instead, for the identical reasons as the XLSB
fixture above.

**Source:** `tests/date.ods`,
`https://raw.githubusercontent.com/tafia/calamine/master/tests/date.ods`.
**Retrieved:** 2026-10-12. **License:** MIT (same repository as above).

**Pinned SHA-256:**

```
d65f3198bc73f2fad356e1b097215fc2f9a833fb802638217e5adc27fbba0466
```

**Known content:** one worksheet `Sheet1`, 4 rows, 2 columns; column A is
`date`/`datetime`/`time`-typed cells, column B is `float`.

## XLS

Legacy Excel XLS fixtures are generated at test time by `xlwt` (genuine
BIFF8 binary writer, dev-only dependency) with broker-inventory-shaped
content this repository fully controls -- a true binary-format write,
just not a third-party file, exercised end-to-end (upload -> map ->
confirm -> replay) in `tests/persistence/test_import_intake_api.py`.

## Formula-cell fail-closed behavior (review amendment Finding D)

Verified directly against hand-authored OOXML XML (not inferred): a
formula cell with no cached `<v>` value at all is treated as a wholly
empty cell and its row is trimmed by `skip_empty_area` the same as any
genuinely blank trailing row; a formula cell whose cached value is an
explicit error type (`t="e"`, e.g. `#DIV/0!`) is instead normalized by
calamine to a present empty string (`""`) -- its row is *not* trimmed,
but the cell value itself is blank. Both outcomes reach
`_coerce_cell_for_target` as "no value for this field" and are therefore
both omitted (never a guessed/fabricated value, and never the literal
`#DIV/0!` text). A formula cell that *does*
carry a genuine non-error cached value is surfaced as that exact cached
value, which this importer treats as trustworthy literal data -- the
same as any other cell -- because calamine never evaluates the formula
itself (it only reads what Excel/the authoring application already
computed and stored); this importer does not re-derive or distrust a
value merely because its origin was a formula rather than a typed
literal. This was executed against OOXML (XLSX/XLSB share the OOXML
cell-value model); the pure-Rust `calamine` core uses one shared `Range<
Data>` representation across all four readers, so the same blank-on-no-
value/error behavior is expected, by architecture, for XLS/ODS too --
this was not independently re-executed against hand-authored BIFF8/
OpenDocument formula records in this session (no safe writer exists to
construct such a fixture for either format), so the generic case remains
a documented inference for those two formats rather than a separately
executed proof.
