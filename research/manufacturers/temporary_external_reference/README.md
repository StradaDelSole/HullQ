# Temporary external builder reference

**Status:** temporary, removable research aid only.

This directory contains a minimized derivative of a user-provided external reference file for SLICE-0019 coverage reconciliation.

## Purpose

Use this material only to identify possible manufacturer/yard coverage gaps and naming variants after comparing it with HullQ's independently researched manufacturer universe.

It is **not**:

- production evidence,
- a canonical HullQ source,
- an input to `registry.json`,
- permission to copy technical facts into HullQ,
- evidence that a raw builder string is a distinct manufacturer/legal entity/yard.

Any manufacturer suggested by this reference still requires independent HullQ research and source verification before inclusion.

## Minimized contents

The uploaded source file is deliberately **not** copied verbatim into the repository. It contains 4,250 model rows. For manufacturer-universe gap analysis, the repository derivative is reduced to one row per non-empty raw builder string with only:

- `builder_raw`
- `model_rows` — number of model rows associated with that exact raw builder string
- `first_year_min` — earliest surfaced first-built year among those rows
- `first_year_max` — latest surfaced first-built year among those rows
- `sample_model` — one example model solely to help disambiguate the raw name

Source-identifying URL fields and technical specifications are omitted.

Current derivative: **2,172 distinct non-empty raw builder strings before normalization/deduplication**.

The index is split into eight CSV shards solely to keep the temporary reference manageable:

- `builder_index/part-01.csv`
- `builder_index/part-02.csv`
- `builder_index/part-03.csv`
- `builder_index/part-04.csv`
- `builder_index/part-05.csv`
- `builder_index/part-06.csv`
- `builder_index/part-07.csv`
- `builder_index/part-08.csv`

## Removal

This directory is intentionally self-contained. If the reference is no longer wanted, delete the entire directory:

`research/manufacturers/temporary_external_reference/`

Removing it must not affect canonical research records, review batches, or `registry.json`.
