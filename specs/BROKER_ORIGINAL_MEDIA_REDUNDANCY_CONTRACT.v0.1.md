# Broker Original-Media Redundancy Contract v0.1

**Status:** READY CANDIDATE  
**Owner decision:** `docs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_PROVIDER_DECISION_2026-10-09.md`  
**Primary implementation slice:** SLICE-0080

## 1. Purpose

Close the accepted pre-real-broker-production requirement that every durable broker-uploaded original/source media object has an independent second copy at a storage provider different from primary Cloudflare R2.

This contract extends the accepted SLICE-0068 marketplace-media model without redefining MediaAsset, MediaPlacement, publication readiness, rights, public serving or Search semantics.

## 2. Storage roles

Exactly two storage roles apply to broker-uploaded source bytes in v0.1:

```text
PRIMARY_ORIGINAL
→ Cloudflare R2
→ existing private original/quarantine object

INDEPENDENT_ORIGINAL_COPY
→ Backblaze B2 EU Central
→ private backup object
```

Processed derivatives remain primary-only and regenerable. YouTube references have no object-storage copy.

Both providers are accessed server-side only through HullQ-owned storage boundaries. Provider endpoint/bucket/account/key values are configuration, never MediaAsset identity.

## 3. Durable database truth

PostgreSQL remains authoritative for whether an accepted MediaAsset has an established independent original copy.

The implementation MUST persist enough operational metadata to distinguish:

1. legacy/pre-SLICE-0080 rows whose independent copy is not established/known; and
2. post-SLICE-0080 rows whose Backblaze B2 original copy was successfully established before database truth was committed.

A concrete schema shape is implementation-level, but it MUST be mechanically impossible for a row to claim an established B2 copy while lacking the durable backup object reference/provider role required to locate it.

Existing rows MUST migrate without fabricating backup success. They remain explicitly unverified/not-established until a later real migration/backfill capability proves otherwise.

The storage provider token may be retained as operational recovery metadata (for example `BACKBLAZE_B2`) but MUST NOT participate in MediaAsset identity.

## 4. Object-key semantics

Server-generated opaque object keys remain mandatory.

The implementation MAY use the same opaque original key in primary R2 and secondary B2, or persist a separate backup key. Whichever shape is chosen:

- callers never choose either authoritative key;
- provider URLs are never stored as identity;
- the database can deterministically locate the established B2 copy;
- retries cannot silently remap an already-established MediaAsset to unrelated backup bytes.

## 5. Synchronous establishment invariant

For every new broker-uploaded original that becomes a durable MediaAsset row:

```text
R2 original write = confirmed success
AND
B2 independent-original write = confirmed success
BEFORE
MediaAsset/redundancy database truth commits
```

This applies to both APPROVED and retained REJECTED MediaAssets because both retain the broker's original/quarantine bytes.

No database row may represent a newly accepted upload with an “established” independent copy based on intention, queued work, retry scheduling or provider documentation alone.

SLICE-0080 deliberately does not introduce asynchronous repair/outbox semantics.

## 6. Failure and orphan semantics

Required fail-closed behavior:

### Primary write fails

- B2 write need not be attempted;
- no MediaAsset row is created;
- error returns without exposing provider credentials/details.

### Primary succeeds, B2 fails or result is unknown

- no MediaAsset row is created;
- no derivative/public placement is created;
- primary object may remain as an unreferenced orphan for later GC;
- the failure is not converted into “backup absent but acceptable.”

### Primary + B2 succeed, processing rejects

- the REJECTED MediaAsset may be persisted only with established redundancy truth;
- neither original is public;
- no derivative is created.

### Primary + B2 succeed, derivative write fails

- no APPROVED MediaAsset row or placement is created;
- original copies and any other successful prior object writes may remain orphaned;
- no database truth claims missing derivative/public state.

### Storage writes succeed, database transaction fails

- database truth remains absent/rolled back;
- unreferenced objects may remain for later cleanup;
- retry must create a new authoritative upload attempt unless the implementation can prove safe idempotent reuse without weakening identity.

## 7. Absence vs dependency error

For B2 configuration and object operations, the following are dependency errors and MUST fail closed rather than be interpreted as confirmed object absence:

- timeout;
- DNS/transport/TLS failure;
- authentication/authorization failure;
- rate limit/quota failure;
- malformed/unexpected provider response;
- endpoint/region mismatch;
- bucket/configuration failure;
- SDK/client error not explicitly classified as a confirmed object-not-found response.

A confirmed object absence may be represented only when the storage adapter receives the provider's documented not-found condition for the exact requested key.

Upload establishment does not need a prior absence check; successful PUT completion is the establishment event. If implementation adds a post-write verification read/head, any verification dependency error fails the upload closed.

## 8. Retry / replay

A browser or API retry after a failed upload is a new attempt unless an accepted existing idempotency key already controls that request. SLICE-0080 does not invent a new cross-request idempotency product contract.

Within one attempt:

- each authoritative key is generated server-side;
- no partial provider success advances database state;
- retrying a provider call must not mutate an already-persisted MediaAsset's storage identity;
- duplicate bytes do not imply duplicate MediaAsset identity;
- same-Organization MediaAsset reuse continues to reference the existing asset and MUST NOT create a second backup copy.

## 9. Public/read boundary

Public and broker-preview media reads continue to use the accepted primary processed derivative path.

Backblaze B2:

- is never a public serving origin in SLICE-0080;
- is never exposed through a browser URL;
- never satisfies cover/public-readiness by itself;
- never weakens rights/processing/retirement checks;
- is used only as independent original/source durability.

Automatic failover/read-from-B2 and a full restore operator workflow are separate later recovery capabilities unless required by a real Production Readiness proof.

## 10. Retirement and purge compatibility

Retiring a MediaAsset continues to prevent new reuse/public usability under the accepted D24 behavior.

SLICE-0080 does not implement the full timed purge/legal-hold worker. It MUST, however, preserve enough durable B2 location metadata that a future purge can delete both the primary original and independent B2 copy without guessing.

No implementation may delete the B2 copy merely because a placement is removed; placement removal is still not asset deletion.

## 11. Provider configuration

Backblaze B2 production configuration must be fail-fast and separate from Cloudflare R2 credentials.

Expected configuration includes:

```text
endpoint
exact S3 region identifier returned by Backblaze
application key ID
application key secret
private bucket
```

The real account must be created in Backblaze **EU Central**. The exact S3 endpoint/cluster suffix is runtime configuration obtained from Backblaze and MUST NOT be hardcoded in domain logic.

Ordinary CI MUST NOT require live Backblaze credentials. Deterministic tests use distinct injected/fake primary and backup stores. A live provider connection belongs to the Production Launch Pack/operator evidence when credentials exist.

## 12. Adapter boundary

The existing `ObjectStorage` protocol remains the common byte-store behavior boundary.

SLICE-0080 may add Backblaze-specific configuration and adapter construction, and may factor shared S3-client plumbing to avoid duplicate provider code. It MUST NOT create a second media domain model or make the domain depend on boto3/provider URLs.

The application/FastAPI wiring must distinguish primary storage from independent-original storage explicitly; passing the same resolved Cloudflare R2 store for both roles is not a valid production configuration.

## 13. Security/privacy

- B2 bucket is private.
- No credentials or provider error payloads leak to API/browser/logs.
- Dedicated least-privilege B2 application key is the production direction.
- Raw originals remain private and may contain metadata that is stripped from public derivatives; therefore the B2 backup is subject to the same private-source-media sensitivity as the primary quarantine object.
- Existing Organization authorization/MFA/CSRF/upload-size/rate-limit boundaries remain unchanged.

## 14. Acceptance proof matrix

Implementation evidence must execute at least:

1. primary succeeds + B2 succeeds → DB row records established redundancy;
2. primary fails → no B2-dependent DB truth, no MediaAsset;
3. primary succeeds + B2 fails → no MediaAsset/placement;
4. B2 auth/network/timeout-style error → fail closed, not absence;
5. both originals succeed + image rejected → REJECTED row retains established redundancy;
6. both originals succeed + derivative fails → no approved row/placement;
7. all object writes succeed + DB insert/transaction fails → no database truth;
8. legacy migrated MediaAsset → never falsely marked backed up;
9. same-Organization asset reuse → no duplicate backup write;
10. public/broker derivative reads never fetch B2 original;
11. retirement preserves backup location for future purge;
12. primary and backup store production construction cannot resolve to the same Cloudflare R2 configuration;
13. missing/malformed B2 configuration fails fast without secrets in errors;
14. migration/schema constraints reject impossible “backup established but no backup locator/provider” shapes;
15. normal repository validation/CI/reproducibility remain green.

## 15. Explicit non-goals

- full backup backfill of historical/test MediaAssets;
- automatic read failover to B2;
- complete disaster-recovery restore orchestration;
- timed retention/purge/legal-hold worker;
- provider-side Object Lock policy;
- derivatives duplicated to B2;
- owner-direct media;
- direct video;
- changes to media rights/publication eligibility;
- creation/provisioning of the real Backblaze account/bucket/key;
- advancing the Production Launch Pack phase;
- any external production data or pilot.
