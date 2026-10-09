# Broker Original-Media Redundancy Provider Decision — 2026-10-09

**Status:** OWNER_ACCEPTED  
**Decision:** Backblaze B2, EU Central, as the independent second provider for broker original/source media  
**Primary media provider remains:** Cloudflare R2  
**Applies to:** SLICE-0080 and later production media operations until explicitly superseded

## Decision

HullQ will use:

```text
primary marketplace media storage
→ Cloudflare R2

independent second copy of broker original/source media
→ Backblaze B2
→ EU Central account region
→ private bucket
→ S3-compatible API
```

This satisfies the accepted architecture requirement that, before real broker production, original/source media has an independent copy at a different storage provider.

Backblaze B2 is selected because the Project Owner's budget is extremely constrained and B2's usage-based object-storage model is more appropriate for a low-volume archival copy than adding a fixed monthly Spaces commitment solely for redundancy.

## Provider facts verified at decision time

Verified against Backblaze's current documentation on 2026-10-09:

- B2 exposes an S3-compatible HTTPS API with endpoints of the form `https://s3.<region>.backblazeb2.com`;
- S3-compatible authentication uses manually created application keys rather than the account master key;
- an application key may be bucket-restricted;
- a B2 account is associated with one data region;
- EU Central stores account data in Amsterdam, Netherlands;
- the region is selected for the account and cannot later be changed in-place.

Operational setup MUST therefore choose **EU Central when the HullQ B2 account is created**. Runtime configuration must use the exact bucket endpoint/region values returned by Backblaze rather than inventing or hardcoding a cluster suffix.

Provider references:

- Backblaze S3-Compatible API: https://www.backblaze.com/docs/en/cloud-storage-call-the-s3-compatible-api
- Backblaze S3-compatible app keys: https://www.backblaze.com/docs/cloud-storage-s3-compatible-app-keys
- Backblaze data regions: https://www.backblaze.com/docs/cloud-storage-data-regions

## Architectural role

Backblaze B2 is a **redundancy provider**, not HullQ domain identity.

The following remain authoritative:

- PostgreSQL: MediaAsset/MediaPlacement metadata and redundancy truth;
- Cloudflare R2: primary original/quarantine and derivative object storage;
- Backblaze B2: independent second copy of original/source bytes only.

Provider URLs, bucket names, account IDs, key IDs and endpoint strings MUST NOT become MediaAsset identity.

A future accepted provider migration may replace B2 without redefining MediaAsset identity. Durable operational metadata may record which provider/storage role contains a copy so recovery remains possible.

## Copy scope

The mandatory independent copy covers broker-uploaded original/source bytes, including an upload that later becomes a retained REJECTED MediaAsset.

The mandatory second copy does **not** cover:

- reproducible processed derivatives;
- structured YouTube references;
- virtual Broker-CI slides;
- owner-direct media, which remains a separate later product boundary.

## Write semantics

For a newly accepted broker upload path after SLICE-0080:

```text
primary R2 original write succeeds
AND
independent B2 original write succeeds
BEFORE
MediaAsset database truth may claim the upload/redundancy exists
```

A B2 timeout, authentication error, transport error, quota/permission error, malformed response or other unknown failure is **not** equivalent to absence and MUST fail closed.

No background/eventual-repair promise is accepted as a substitute for the required second copy in SLICE-0080.

If one storage write succeeds and a later required step fails, unreferenced storage objects may remain as orphans for later cleanup; PostgreSQL must not falsely claim a complete MediaAsset/redundancy state.

## Runtime/secret direction

Expected production secret/configuration names may include names equivalent to:

```text
HULLQ_MEDIA_BACKUP_B2_ENDPOINT
HULLQ_MEDIA_BACKUP_B2_REGION
HULLQ_MEDIA_BACKUP_B2_KEY_ID
HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY
HULLQ_MEDIA_BACKUP_B2_BUCKET
```

Exact secret values never belong in the repository.

Production setup later must use a dedicated least-privilege B2 application key restricted to the HullQ media-backup bucket as far as Backblaze's S3-compatible permission model permits.

## Production Launch Pack consequence

This decision does not provision an account, bucket, application key or production secret and therefore does not advance the Production Launch Pack phase.

```text
PRODUCTION_LAUNCH_PACK_PHASE = NOT_STARTED
```

The account/ownership/MFA/recovery/billing evidence belongs to Phase 1. Bucket/key/connectivity evidence belongs to later applicable phases.

## Supersession rule

Changing from Backblaze B2 to another secondary provider before implementation completion requires explicit Owner approval and readiness reconciliation. Changing provider after real media has been written additionally requires a retained migration/recovery plan so existing copies do not become undiscoverable.
