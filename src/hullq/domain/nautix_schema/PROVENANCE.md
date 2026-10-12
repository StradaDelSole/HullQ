# NautiX 1.4 XSD — pinned provenance (SLICE-0083)

**File:** `NautiX_v1.4.xsd` in this directory.

**Source URL:** `https://nautix.nautic-network.org/v1.4/NautiX.xsd` (the exact
URL named by the slice contract and by
`docs/POST_SLICE_0082_IMPORT_REASSESSMENT_2026-10-12.md`).

**Retrieved:** 2026-10-12, by this implementation, via a direct HTTPS GET
(byte-for-byte; not reconstructed from documentation prose or an AI
summary).

**Server-reported metadata at retrieval time** (`curl -I`):

- `Last-Modified: Thu, 09 Jul 2026 13:19:44 GMT` — matches the "last
  modified 9 July 2026" the slice contract records for NautiX 1.4.
- `Content-Length: 153144`
- `ETag: "25638-6562d7a39e0bf"`

**Pinned file size:** 153144 bytes — matches `Content-Length` exactly.

**Pinned SHA-256:**

```
249fd6693fd032dc71d5138b64a39a3b018ffdf8e3c733101e95f6e4a2ddb91f
```

`hullq.domain.import_nautix` hardcodes this exact digest and verifies the
packaged file against it at first use (`_load_pinned_schema`), failing
closed if the on-disk asset ever diverges from this pin -- the runtime
validator never fetches the XSD over the network and never falls back to a
hand-written "schema-like" subset validator.

**Reproduce the pin:**

```
curl -fsSL -o NautiX_v1.4.xsd https://nautix.nautic-network.org/v1.4/NautiX.xsd
sha256sum NautiX_v1.4.xsd
```

A future NautiX schema revision is a new, deliberately versioned pin
(a new file/digest/provenance entry), never a silent in-place replacement
of this one.
