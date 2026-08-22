# Temporary external builder/model reference

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

The uploaded source file is deliberately **not** copied verbatim into the repository. The derivative retains only:

- `builder_raw`
- `boat_model`
- `first_built`

Source-identifying URL fields and all technical specification fields are omitted.

Current derivative size: **4,250 model rows** representing **2,173 distinct raw builder strings** before normalization/deduplication.

The rows are split into five CSV shards solely to keep the temporary reference manageable:

- `builder_model_year/part-01.csv`
- `builder_model_year/part-02.csv`
- `builder_model_year/part-03.csv`
- `builder_model_year/part-04.csv`
- `builder_model_year/part-05.csv`

## Removal

This directory is intentionally self-contained. If the reference is no longer wanted, delete the entire directory:

`research/manufacturers/temporary_external_reference/`

Removing it must not affect canonical research records, review batches, or `registry.json`.
