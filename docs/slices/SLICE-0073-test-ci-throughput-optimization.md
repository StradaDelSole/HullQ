# SLICE-0073 — Test / CI Throughput Optimization

**Type:** ENGINEERING / CI / TEST INFRASTRUCTURE  
**Status:** READY — INDEPENDENT READINESS REVIEW PASS  
**Base:** post-SLICE-0072 canonical main  
**Primary contract:** `specs/TEST_CI_THROUGHPUT_OPTIMIZATION.v0.1.md`

## Goal

Remove the current validation-throughput bottleneck before additional feature slices while preserving HullQ's final acceptance bar.

## Problem statement

At SLICE-0072 closure the GitHub PR critical path is dominated by one serialized PostgreSQL job at 7m21s–8m22s, while local complete PostgreSQL-backed backend validation has repeatedly taken roughly 38–45 minutes.

This cost materially slows amendments and slice throughput.

## Required implementation

1. instrument/retain baseline and resulting test-group timings;
2. introduce explicit backend test grouping suitable for deterministic execution;
3. safely parallelize PostgreSQL-dependent work using isolated mutable state;
4. combine branch coverage deterministically and enforce the existing 90% threshold;
5. remove unnecessary duplicate broad execution while retaining cross-platform confidence;
6. separate independent CI work into parallel jobs;
7. reconcile historical research/bootstrap replay out of the ordinary product critical path where a documented dependency boundary permits;
8. provide a supported local/Claude final-validation route that benefits from the same safe partitioning;
9. update CI/test engineering documentation to match the resulting system.

## Implementation freedom

Claude may choose the exact shard count, scripts and GitHub Actions topology after measurement.

Prefer the simplest solution that produces a material wall-clock improvement and is understandable to future maintainers.

Do not introduce distributed test infrastructure or external paid CI services.

## Mandatory constraints

- no production/domain behavior changes;
- no coverage-floor reduction;
- no meaningful test deletion;
- no unsafe same-schema PostgreSQL concurrency;
- no weakening of dependency/security gates;
- no mutable live-network dependency;
- no required-check path-filter trap;
- no final-candidate merge without broad aggregate evidence.

## Validation

The final implementation report must include:

- exact before/after CI timings;
- exact before/after local timing where reproducible;
- shard/group definitions;
- proof of PostgreSQL isolation;
- aggregate test counts;
- aggregate coverage;
- retained proof/research-replay routing;
- all remote required-check results;
- exact implementation HEAD.

## Stop conditions

Stop and report rather than weakening safety if:

- a persistence test cannot be safely isolated;
- combined coverage is not mechanically trustworthy;
- required-check semantics would become ambiguous;
- moving a retained replay off every PR cannot be justified by a dependency boundary.

## Non-goals

SLICE-0073 adds no HullQ marketplace capability. After closure, normal product capability selection resumes through fresh reconciliation.
