# HullQ Controlled Benchmark — Research Wave 01

**Date:** 2026-08-20  
**Designs:** 5  
**Structured observations:** 58

## Designs

- Hallberg-Rassy 36
- Westerly Centaur
- RM 1180
- Najad 34
- J/24

## Method

Independent research was performed first across manufacturer, archive, specialist, broker and community sources. SailboatData was consulted only afterward as a reference comparison. No SailboatData field value is stored as HullQ evidence or used as a missing-value fallback; only comparison outcomes are retained.

## Findings

### Hallberg-Rassy 36

The manufacturer exposes explicit Mk I/Mk II generation boundaries plus option-sensitive dimensions. Reference comparison agrees on several common fields but disagrees on some dimensions and does not preserve the full generation/option semantics.

### Westerly Centaur

Core dimensions are stable, but rudder evidence suggests a production-time change: original designer material describes a skegless spade rudder while later specialist material reports skeg support on later boats. This remains a generation/time-boundary research case.

### RM 1180

The builder and specialist material expose combinatorial appendage options rather than one keel/rudder pair. A flat configuration record loses real factory choices.

### Najad 34

The official multilingual Najad PDF conflicts internally on production count (English/Swedish versus German). Displacement remains intentionally unresolved pending stronger design-level evidence rather than using an individual-boat or reference value as a fallback.

### J/24

Manufacturer nominal displacement and an ORC measurement/rating displacement are different measurement bases and must not be collapsed into a single scalar conflict.

## Architecture implications

Wave 01 confirms that generation identity, configuration scope, raw measurement basis, explicit unresolved states and field-level provenance are required in ordinary real-world research, not merely hypothetical edge cases.

This wave is research evidence, not canonical production data.
