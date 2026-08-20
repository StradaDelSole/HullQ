# Legacy Structured Observation Exports — Waves 01–02

These files preserve the exact structured JSONL observation exports created during the first two SLICE-0011 research waves **before** the benchmark-derived `ResearchEvidenceBundle` contract exists.

They are retained for reproducibility and later migration testing. They are **not canonical FieldEvidence**, do not define the future importer contract, and MUST NOT be treated as production data.

## Files

- `WAVE-01-observations.jsonl.gz.b64`
  - decoded JSONL rows: 58
  - SHA-256 of decoded original JSONL: `0b619574d6272ffa5bbf7246511ac4397e3081b1bdf019c0898d9c0266c0b804`
- `WAVE-02-observations.jsonl.gz.b64`
  - decoded JSONL rows: 138
  - SHA-256 of decoded original JSONL: `1cd8745aa413e1525f47a481de95d2a86546497696a58bb99b3d036de011a81c`

The files are gzip-compressed JSONL encoded as single-line Base64 text so the exact research exports can be retained through the repository's UTF-8 text write path.

Example reconstruction on a POSIX shell:

```bash
base64 -d WAVE-01-observations.jsonl.gz.b64 | gzip -dc > WAVE-01-observations.jsonl
base64 -d WAVE-02-observations.jsonl.gz.b64 | gzip -dc > WAVE-02-observations.jsonl
```

## Important semantics

- The exports contain independently researched HullQ observations and source URLs.
- SailboatData appears only through comparison-result labels/outcomes; no SailboatData field value is used as HullQ evidence or fallback data.
- Wave 01 and Wave 02 use slightly different ad-hoc key shapes because they predate the benchmark-derived bundle contract. That difference is intentional historical evidence for why SLICE-0012 defines one versioned handoff schema.
- Do not normalize these files in place. SLICE-0012 should define explicit migration into the successor evidence/applicability + ResearchEvidenceBundle contract.
- Waves 03–06 currently retain source-linked research in their audited wave summaries. After SLICE-0012 freezes the bundle contract, the master/research role can encode the full 50-design corpus into that contract without inventing new web evidence.
