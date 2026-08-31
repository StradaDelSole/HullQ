# Listings Port competitive evidence — search integrity, configuration scope, and asset lineage

**Date:** 2026-08-31  
**Status:** retained competitive-research evidence; non-authorizing for automated access; not a legal finding  
**Purpose:** preserve only the observations that materially affect HullQ product validation, market strategy, and future research design.

## Executive conclusion

Listings Port remains a useful benchmark for broad sailboat aggregation, but exploratory testing exposed concrete weaknesses in search precision, entity resolution, hard-constraint enforcement, and configuration scoping. Separately, three independently selected sailboat drawings showed materially identical decoded image content between SailboatData-associated assets and Listings Port-served assets, with a repeated reprocessing fingerprint on two JPEG cases and 100% pixel-identical content in a lossless GIF case.

These findings do **not** establish copyright infringement, license status, direct download direction, or the ultimate copyright owner. They do establish useful internal evidence that Listings Port's breadth/content-richness should not be treated as proof that reliable technical search has been solved, and that some visual assets share the same underlying image source rather than being independently generated illustrations.

No change is made to the accepted Product Execution Plan. The immediate sequence remains SLICE-0038 -> bounded Seed Corpus -> Concierge Validation, with Market Access research parallel and non-blocking.

---

## 1. Evidence classes and wording rules

Keep these categories separate:

1. **Observed product behavior** — what the UI/search returned during a timestamped exploratory test.
2. **Technical inference** — plausible explanation for the behavior, not an established implementation fact.
3. **Asset-lineage evidence** — image-content comparison showing common underlying image content.
4. **Rights/licensing status** — unknown unless independently established by a controlling source or written permission.
5. **Strategic consequence for HullQ** — internal product decision, not a public accusation or marketing claim.

Do not state that Listings Port scraped SailboatData, stole images, infringed copyright, violated database rights, or lacks licenses unless future evidence directly establishes the relevant proposition.

---

## 2. Search-integrity observations

### 2.1 Hard price constraint

Exploratory query:

```text
bluewater cruiser under 30000 EUR
```

Observed standard-search results included boats materially above the stated budget, up to approximately EUR 177k, plus records without price. In the separate question flow, the visible recognized price constraint was shown as approximately `<= 33,000 $usd`, not the requested EUR 30,000; length, SA/D and capsize-ratio suggestions appeared separately.

**Internal significance:** a hard numeric buyer constraint must not be treated as fuzzy relevance. HullQ should preserve a visible distinction between hard requirements, preferences, free-text context, and UNKNOWN.

### 2.2 Draft + length constraint

Exploratory query:

```text
shallow draft under 1.2m AND offshore capable AND LOA over 40ft
```

Observed standard-search results included boats with draft values above 1.2 m, including approximately 1.42, 1.52, 1.57, 1.64 and 2.13 m. The separate question flow appeared better at extracting explicit numeric constraints but displayed malformed unit strings such as `mft` and added optional domain recommendations.

**Internal significance:** for HullQ, `Draft <= 1.20 m` must mean exactly that. Values above the bound are FALSE; missing/unresolved values are UNKNOWN; semantic similarity must not soften a hard constraint.

### 2.3 BoatDesign identity resolution

Exploratory query intended to target:

```text
Beneteau Oceanis 30.1
Draft <= 1.60 m
```

The UI displayed/returned `Beneteau Oceanis 300`, a different design/model identity.

**Internal significance:** this is a direct benchmark for HullQ's identity model. Fuzzy lexical similarity must never silently replace exact BoatDesign identity. Similar designs may be shown separately as recommendations, never merged into the exact result set.

### 2.4 Negation

Exploratory query:

```text
family cruiser, NOT a catamaran, under 40ft, forgiving for beginners
```

Observed results included a catamaran and a very broad result set.

**Internal significance:** explicit categorical negation is a hard semantic constraint when the query parser accepts it as such. `NOT catamaran` must exclude confirmed catamarans; unresolved hull type remains UNKNOWN rather than being treated as eligible by guesswork.

---

## 3. Tartan 37 configuration-scope case

A search for `Tartan 37` returned a fuzzy set including Tartan 37, Tartan 3700, Tartan 372 and unrelated `37`-named designs from other builders. This is useful evidence that a broad corpus can still provide weak exact-model search if model identity is treated as a text-relevance problem.

More importantly, the Tartan 37 model surface was observed to present a single structured keel/draft representation while its own narrative buyer-guide material discussed multiple factory keel configurations across the production run, including centerboard, deep-fin and shoal/Scheel variants.

**Internal significance:** this is a concrete competitor benchmark for HullQ's configuration model:

```text
BoatDesign has multiple factory configurations
!=
one model-level keel/draft value safely represents every configuration
```

HullQ should preserve configuration-specific facts and must not project design-level option existence onto a concrete physical listing.

---

## 4. Editorial/AI-enrichment observation

Listings Port model pages were observed to include structured buyer-guide sections such as design/construction, rig/handling, accommodation, known weaknesses, refits/ownership, verdict, pros and cons, with named references to sailing publications/authors on some pages.

Comparison work supports a **fan-in synthesis hypothesis** rather than a proven linear copy chain:

```text
structured model facts
       +
multiple external editorial / manufacturer / community sources
       ->
LLM or automated synthesis
       ->
model overview / buyer guide / pros-cons
```

No direct verbatim-copy finding is retained here. The relevant HullQ lesson is not to copy this content-generation model blindly: rich generated prose can obscure source applicability, time scope, variant scope and physical-listing scope unless every accepted fact retains provenance and qualification.

---

## 5. Image-asset lineage evidence

Three independently chosen models were compared between SailboatData-associated drawings and Listings Port-served drawings. The purpose was not to establish legal liability but to test whether Listings Port's drawings were independently generated or shared the same underlying image assets.

### 5.1 Southerly 115

Reported comparison:

- identical dimensions: `330 x 754 px`;
- approximately 73% of pixels exactly identical;
- approximately 95% within ordinary JPEG recompression tolerance;
- SailboatData-associated version: RGB with richer EXIF/compression metadata;
- Listings Port version: grayscale JPEG with simpler JFIF header and no EXIF;
- independent third-party material was found attributing the same Southerly 115 layout image to SailboatData.

**Conclusion:** materially identical underlying drawing content; consistent with re-encoding/reprocessing rather than independent redraw/generation. Direct acquisition path and licensing remain unknown.

### 5.2 Freedom 40 CC

Reported comparison:

- identical dimensions: `452 x 780 px`;
- approximately 76.7% of pixels exactly identical;
- approximately 95.4% within JPEG recompression tolerance;
- the same broad metadata pattern repeated: richer RGB/EXIF source-side file versus grayscale/JFIF Listings Port-side file.

**Conclusion:** second independent model showing the same underlying image content and a similar reprocessing fingerprint. This materially weakens the independent-generation hypothesis.

### 5.3 Nonsuch 30

Reported comparison:

- identical dimensions: `360 x 641 px`;
- **100.0% pixel-identical decoded image content** in a lossless GIF comparison;
- the files themselves were not asserted to be byte-identical because container/extension metadata differed; the SailboatData-associated file contained a `NETSCAPE2.0` extension block that the Listings Port-side file did not.

**Conclusion:** the decoded visual content is identical; independent recreation is not a credible explanation for this case. Container differences are consistent with resaving/reprocessing of the same image content.

### 5.4 Combined inference

Across three independent models, the retained evidence supports:

> Listings Port serves drawings that share the same underlying image content as SailboatData-associated drawings for all three tested models, with a repeated reprocessing pattern in the JPEG cases.

It does **not** by itself establish:

- that Listings Port downloaded directly from SailboatData;
- who owns copyright in the original drawings;
- whether the assets originated from a builder/designer and were independently licensed by multiple parties;
- whether Listings Port has permission or a license;
- how widespread the pattern is beyond the three tested cases.

Because the business conclusion no longer changes materially with a fourth/fifth example, further image-lineage testing is not prioritized now.

### Evidence-retention rule

Do not commit third-party drawings into the HullQ repository merely to preserve this research unless rights to retain them are separately cleared. Preserve derived comparison metrics, source URLs, hashes where lawfully retained, timestamps, and reproducible methodology instead.

---

## 6. Competitive interpretation

The earlier shorthand `aggregation moat is dead` is rejected as too strong.

A more accurate model is that **aggregation alone is insufficient**, while broad lawful inventory coverage remains a valuable moat component when combined with search integrity.

Potential HullQ moat stack:

```text
broad market coverage
+
exact BoatDesign identity
+
configuration-aware technical truth
+
deterministic hard-constraint enforcement
+
explicit UNKNOWN / conflict handling
+
auditable provenance
+
good search UX
+
saved search / fit-confirmed monitoring
```

Listings Port is evidence that breadth, dedup, market history and alerts are valuable. The exploratory tests are evidence that breadth does not automatically imply reliable exact technical search.

The intended long-term HullQ ambition therefore remains capable of being broader than a narrow reference database:

> search a large share of the real sailboat market by real technical requirements, with materially better truth semantics and UX.

This is an ambition, not a currently validated market claim.

---

## 7. Product/roadmap consequences

### Immediate

No roadmap change. Do not interrupt SLICE-0038 or add Listings Port as a live source.

### Seed Corpus

Use technically discriminating models/configurations that expose identity and configuration differences, not only popular models. Tartan 37-like multi-configuration designs are useful stress cases.

### Concierge validation

Retain three competitor benchmark classes for moderated user tests:

1. **hard numeric constraint** — e.g. budget/draft limits;
2. **exact identity + configuration** — e.g. Oceanis 30.1 vs Oceanis 300 and configuration-specific draft;
3. **categorical negation** — e.g. `NOT catamaran`.

Do not tell participants that Listings Port is `wrong` before observation. Show comparable outputs neutrally and measure Decision Impact, Monitoring Pull and Trust Advantage under the accepted Gate 1 protocol.

### Market Access

Do not infer HullQ's acceptable risk posture from a competitor's apparent behavior. HullQ's Market Access track still evaluates APIs, broker/CRM/MLS feeds, portal/data partnerships and explicit rights separately.

A future founder-level risk decision may distinguish between:

- legal/contractual risk tolerance for data acquisition;
- non-negotiable truth integrity once HullQ displays a technical claim.

### Automation / coverage speed

The competitor research suggests a useful future question: how much manufacturer/review/source discovery and extraction can AI automate while HullQ's admission layer continues to decide whether a fact is accepted, qualified, conflicting or UNKNOWN.

Preferred principle:

```text
AI may accelerate discovery/extraction.
AI does not get to manufacture Search Truth.
```

This should be evaluated only when it becomes the active product/coverage bottleneck under the Product Execution Plan; it is not a reason to reopen architecture work now.

---

## 8. Research stop decision

This competitive-research pass is considered sufficient for current product decisions.

Further Listings Port teardown is not prioritized before:

1. SLICE-0038 completion;
2. bounded Seed Corpus creation;
3. real Concierge Validation.

Reopen only if a material new external fact could change the product thesis, market-access strategy, or accepted rights posture.
