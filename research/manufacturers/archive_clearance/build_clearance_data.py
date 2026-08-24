#!/usr/bin/env python3
"""Build archive_source_clearance.json from the ChatGPT-led external research findings
supplied for SLICE-0020, transcribed into the accepted schema structure.

Claude performed no independent external research to produce this data: every
finding, evidence surface, and use-specific decision below is a direct
transcription of the external research pass's supplied result. This script
only performs repository-local structural transcription plus the deterministic
ADAPTER_READY recomputation defined by the SLICE-0020 classification vocabulary
(so adapter_classification is never asserted without a checkable basis).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SCHEMA_PATH = HERE / "archive_source_clearance_schema.json"
OUT_PATH = HERE / "archive_source_clearance.json"

REVIEW_DATE = "2026-08-24"
GENERATED_AT = "2026-08-24T00:00:00Z"

UNRETRIEVED_AUTOMATION_NOTE = (
    "Individual robots.txt contents were not retained as reliable evidence during "
    "the ChatGPT-led external research pass. No explicit automated/bulk permission "
    "was found for this source. Recorded as unknown/unretrieved per the general "
    "rights rule rather than inferred from public HTML accessibility, sitemap "
    "availability, search-engine indexing, or source prestige."
)


def surfaces(host: str, paths: list[str]) -> list[dict[str, str]]:
    return [{"host": host, "path": path, "url": f"https://{host}{path}"} for path in paths]


def adapter_ready_test(decisions: dict[str, str]) -> dict[str, Any]:
    identity_seed_allowed = decisions["identity_seed"] == "allowed"
    automated_ingestion_allowed = decisions["automated_ingestion"] == "allowed"
    # No source in this pilot has an explicit contradictory field recorded once the two
    # gating clearances above are already non-allowed, so this remains vacuously true
    # unless a future re-review sets both clearances to allowed.
    no_contradiction = True
    bulk_ok = decisions["bulk_bootstrap"] == "allowed"
    result = identity_seed_allowed and automated_ingestion_allowed and no_contradiction and bulk_ok
    return {
        "identity_seed_allowed": identity_seed_allowed,
        "automated_ingestion_allowed": automated_ingestion_allowed,
        "no_contradictory_access_permission_field": no_contradiction,
        "bulk_bootstrap_allowed_or_bounded_conditions_documented": bulk_ok,
        "result": result,
    }


SOURCES: list[dict[str, Any]] = [
    {
        "source_key": "catalina_yachts",
        "source_display_name": "Catalina Yachts",
        "evidence_surfaces": surfaces(
            "www.catalinayachts.com", ["/brochure-archives/", "/history/", "/sport-series/"]
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Official manufacturer archive; broad brochure index with many historical production models; public access.",
            "evidence_urls": ["https://www.catalinayachts.com/brochure-archives/"],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": None,
            "note": "No explicit open licence or source-specific automated/bulk reuse permission was found during the bounded research pass.",
            "evidence_urls": ["https://www.catalinayachts.com/brochure-archives/"],
        },
        "automation_evidence": {
            "robots_or_api_status": "unknown_unretrieved",
            "note": UNRETRIEVED_AUTOMATION_NOTE + " No retained automation/API clearance.",
        },
        "research_finding_note": (
            "Official manufacturer archive; broad brochure index with many historical production "
            "models; public access; no explicit open licence or source-specific automated/bulk "
            "reuse permission was found during the bounded research pass; no retained "
            "automation/API clearance."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "conditional",
            "production_value": "conditional",
            "automated_ingestion": "unknown",
            "bulk_bootstrap": "legal_review_required",
            "artifact_redistribution": "legal_review_required",
        },
        "systematic_use_status": "REQUIRES_REVIEW",
        "adapter_classification": "RESEARCH_ONLY / REVIEW_REQUIRED",
    },
    {
        "source_key": "pearson_yachts",
        "source_display_name": "Pearson Yachts",
        "evidence_surfaces": surfaces(
            "www.pearsonyachts.org", ["/", "/pearson-sailboats.html", "/models/pearson-26od.html"]
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Volunteer/non-profit Pearson owners archive for the defunct Pearson Yachts Corporation; all-model table with dedicated model pages and factory brochures; publicly accessible.",
            "evidence_urls": ["https://www.pearsonyachts.org/pearson-sailboats.html"],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": "Site footer states Copyright ©2020 All Rights Reserved.",
            "note": (
                "Explicitly states that it preserves enhanced original builder documentation plus "
                "owner contributions and internet research; mixed rightsholder/archive character "
                "means original factory documents and owner material MUST NOT be treated as one "
                "open-licensed dataset. No automated/bulk permission found."
            ),
            "evidence_urls": ["https://www.pearsonyachts.org/"],
        },
        "automation_evidence": {
            "robots_or_api_status": "unknown_unretrieved",
            "note": UNRETRIEVED_AUTOMATION_NOTE,
        },
        "research_finding_note": (
            "Volunteer/non-profit Pearson owners archive for the defunct Pearson Yachts Corporation; "
            "explicitly states that it preserves enhanced original builder documentation plus owner "
            "contributions and internet research; all-model table with dedicated model pages and "
            "factory brochures; site footer states Copyright ©2020 All Rights Reserved; mixed "
            "rightsholder/archive character means original factory documents and owner material MUST "
            "NOT be treated as one open-licensed dataset; no automated/bulk permission found."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "conditional",
            "production_value": "legal_review_required",
            "automated_ingestion": "unknown",
            "bulk_bootstrap": "legal_review_required",
            "artifact_redistribution": "legal_review_required",
        },
        "systematic_use_status": "REQUIRES_REVIEW",
        "adapter_classification": "RESEARCH_ONLY / REVIEW_REQUIRED",
    },
    {
        "source_key": "oyster_yachts",
        "source_display_name": "Oyster Yachts",
        "evidence_surfaces": surfaces(
            "oysteryachts.com",
            ["/heritage-yachts/", "/heritage-yachts/oyster-46/", "/heritage-yachts/oyster-545/"],
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Official manufacturer heritage catalogue; explicitly describes 46 luxury sailboat models; model pages contain years, hull counts and dimensions.",
            "evidence_urls": ["https://oysteryachts.com/heritage-yachts/"],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": "Current site footer carries © 2026 OYSTER YACHTS.",
            "note": "No general open data licence or explicit automated/bulk reuse permission found.",
            "evidence_urls": ["https://oysteryachts.com/heritage-yachts/"],
        },
        "automation_evidence": {
            "robots_or_api_status": "unknown_unretrieved",
            "note": UNRETRIEVED_AUTOMATION_NOTE,
        },
        "research_finding_note": (
            "Official manufacturer heritage catalogue; explicitly describes 46 luxury sailboat "
            "models; model pages contain years, hull counts and dimensions; current site footer "
            "carries © 2026 OYSTER YACHTS; no general open data licence or explicit "
            "automated/bulk reuse permission found."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "conditional",
            "production_value": "conditional",
            "automated_ingestion": "unknown",
            "bulk_bootstrap": "legal_review_required",
            "artifact_redistribution": "legal_review_required",
        },
        "systematic_use_status": "REQUIRES_REVIEW",
        "adapter_classification": "RESEARCH_ONLY / REVIEW_REQUIRED",
    },
    {
        "source_key": "westerly_marine",
        "source_display_name": "Westerly Marine / Westerly Owners Association",
        "evidence_surfaces": (
            surfaces("wiki.westerly-owners.co.uk", ["/index.php?title=Main_Page"])
            + surfaces("westerly-owners.co.uk", ["/terms-and-conditions/"])
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Westerly Wiki is sponsored by the Westerly Owners Association; states it contains most Westerly brochures ever made and at least one brochure for every model; includes original brochures/manuals and owner-created technical material.",
            "evidence_urls": ["https://wiki.westerly-owners.co.uk/index.php?title=Main_Page"],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": (
                "WOA Terms state articles and technical contributions are published for members' "
                "interest and are not validated by WOA."
            ),
            "note": "No general automated/bulk reuse grant found; mixed original-factory/association/contributor rights remain material.",
            "evidence_urls": ["https://westerly-owners.co.uk/terms-and-conditions/"],
        },
        "automation_evidence": {
            "robots_or_api_status": "unknown_unretrieved",
            "note": UNRETRIEVED_AUTOMATION_NOTE,
        },
        "research_finding_note": (
            "Westerly Wiki is sponsored by the Westerly Owners Association; it states that it "
            "contains most Westerly brochures ever made and at least one brochure for every model; "
            "includes original brochures/manuals and owner-created technical material; WOA Terms "
            "state articles and technical contributions are published for members' interest and are "
            "not validated by WOA; no general automated/bulk reuse grant found; mixed "
            "original-factory/association/contributor rights remain material."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "conditional",
            "production_value": "legal_review_required",
            "automated_ingestion": "unknown",
            "bulk_bootstrap": "legal_review_required",
            "artifact_redistribution": "legal_review_required",
        },
        "systematic_use_status": "REQUIRES_REVIEW",
        "adapter_classification": "RESEARCH_ONLY / REVIEW_REQUIRED",
    },
    {
        "source_key": "beneteau",
        "source_display_name": "Bénéteau",
        "evidence_surfaces": surfaces(
            "www.beneteau.com",
            [
                "/pt-br/condicoes-de-uso",
                "/en-us/heritage-sailing-yachts/first-1977-1983",
                "/en-us/first-1977-1983/first-18",
            ],
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Official heritage range is public and provides a high-yield model index.",
            "evidence_urls": [
                "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983"
            ],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": (
                "Current Terms of Use state that no element of the site may be used, reproduced, "
                "represented, distributed, decompiled, indexed or extracted by any technical "
                "protocol without prior written consent. The Terms also prohibit permanent or "
                "temporary extraction of all or a qualitatively/quantitatively substantial portion "
                "of the site's databases."
            ),
            "note": (
                "This is explicit negative evidence for the contemplated automated/archive adapter "
                "use; manual research-reference use is distinct from automated production "
                "acquisition."
            ),
            "evidence_urls": ["https://www.beneteau.com/pt-br/condicoes-de-uso"],
        },
        "automation_evidence": {
            "robots_or_api_status": "explicit_prohibition_via_terms",
            "note": (
                "No separate robots.txt/API evidence was retained, but the retained Terms of Use "
                "explicitly name 'technical protocol' indexing/extraction as prohibited without "
                "prior written consent, which this record treats as an explicit terms-based "
                "automation prohibition rather than an unretrieved/unknown default."
            ),
        },
        "research_finding_note": (
            "Official heritage range is public and provides a high-yield model index; current Terms "
            "of Use state that no element of the site may be used, reproduced, represented, "
            "distributed, decompiled, indexed or extracted by any technical protocol without prior "
            "written consent; the Terms also prohibit permanent or temporary extraction of all or a "
            "qualitatively/quantitatively substantial portion of the site's databases; this is "
            "explicit negative evidence for the contemplated automated/archive adapter use; manual "
            "research-reference use is distinct from automated production acquisition."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "legal_review_required",
            "production_value": "legal_review_required",
            "automated_ingestion": "prohibited",
            "bulk_bootstrap": "prohibited",
            "artifact_redistribution": "prohibited",
        },
        "systematic_use_status": "BLOCKED",
        "adapter_classification": "BLOCKED",
    },
    {
        "source_key": "wauquiez",
        "source_display_name": "Wauquiez",
        "evidence_surfaces": surfaces(
            "www.wauquiez.com", ["/une-grande-histoire/", "/mention-legales/"]
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Official manufacturer historical timeline gives many named models and launch eras; publicly accessible.",
            "evidence_urls": ["https://www.wauquiez.com/une-grande-histoire/"],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": (
                "Official legal notice states site content is owned/used by Wauquiez and "
                "reproduction, distribution, modification, adaptation, retransmission or "
                "publication without express written consent is prohibited."
            ),
            "note": "That does not establish automated-ingestion permission; no API or explicit automated/bulk clearance found.",
            "evidence_urls": ["https://www.wauquiez.com/mention-legales/"],
        },
        "automation_evidence": {
            "robots_or_api_status": "unknown_unretrieved",
            "note": UNRETRIEVED_AUTOMATION_NOTE
            + " The legal notice's reproduction/distribution restriction is recorded as rights "
            "evidence, not as a robots.txt/API-specific automation finding.",
        },
        "research_finding_note": (
            "Official manufacturer historical timeline gives many named models and launch eras; "
            "official legal notice states site content is owned/used by Wauquiez and reproduction, "
            "distribution, modification, adaptation, retransmission or publication without express "
            "written consent is prohibited; that does not establish automated-ingestion permission; "
            "no API or explicit automated/bulk clearance found."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "conditional",
            "production_value": "legal_review_required",
            "automated_ingestion": "unknown",
            "bulk_bootstrap": "legal_review_required",
            "artifact_redistribution": "prohibited",
        },
        "systematic_use_status": "REQUIRES_REVIEW",
        "adapter_classification": "RESEARCH_ONLY / REVIEW_REQUIRED",
    },
    {
        "source_key": "elan",
        "source_display_name": "Elan",
        "evidence_surfaces": surfaces(
            "www.elan-yachts.com", ["/en/previous-models", "/en/carbon/history"]
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Official Previous Models and company-history surfaces; history explicitly identifies historical production models and design eras.",
            "evidence_urls": ["https://www.elan-yachts.com/en/previous-models"],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": None,
            "note": "No explicit open data licence or automated/bulk permission found during the bounded pass; public accessibility therefore remains research evidence only.",
            "evidence_urls": ["https://www.elan-yachts.com/en/previous-models"],
        },
        "automation_evidence": {
            "robots_or_api_status": "unknown_unretrieved",
            "note": UNRETRIEVED_AUTOMATION_NOTE,
        },
        "research_finding_note": (
            "Official Previous Models and company-history surfaces; history explicitly identifies "
            "historical production models and design eras; no explicit open data licence or "
            "automated/bulk permission found during the bounded pass; public accessibility therefore "
            "remains research evidence only."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "conditional",
            "production_value": "conditional",
            "automated_ingestion": "unknown",
            "bulk_bootstrap": "legal_review_required",
            "artifact_redistribution": "legal_review_required",
        },
        "systematic_use_status": "REQUIRES_REVIEW",
        "adapter_classification": "RESEARCH_ONLY / REVIEW_REQUIRED",
    },
    {
        "source_key": "cantiere_del_pardo_grand_soleil",
        "source_display_name": "Cantiere del Pardo / Grand Soleil",
        "evidence_surfaces": (
            surfaces("old2.grandsoleil.net", ["/history/"])
            + surfaces(
                "www.grandsoleil.net",
                ["/it/privacy-policy/", "/blogs/sailing-stories/sara-nocella-blu-grand-soleil-34"],
            )
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Official heritage history starts in 1973 and identifies successive model ranges; explicitly records Grand Soleil 34, GS 35, GS 41, GS 39, Jezequel models and later Frers models.",
            "evidence_urls": ["https://old2.grandsoleil.net/history/"],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": "Current Privacy Policy identifies Cantiere del Pardo as controller.",
            "note": "The Privacy Policy is not a content-reuse licence; no explicit automated-ingestion/bulk licence was found.",
            "evidence_urls": ["https://www.grandsoleil.net/it/privacy-policy/"],
        },
        "automation_evidence": {
            "robots_or_api_status": "unknown_unretrieved",
            "note": UNRETRIEVED_AUTOMATION_NOTE,
        },
        "research_finding_note": (
            "Official heritage history starts in 1973 and identifies successive model ranges; it "
            "explicitly records Grand Soleil 34, GS 35, GS 41, GS 39, Jezequel models and later "
            "Frers models; current Privacy Policy identifies Cantiere del Pardo as controller, but is "
            "not a content-reuse licence; no explicit automated-ingestion/bulk licence was found."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "conditional",
            "production_value": "conditional",
            "automated_ingestion": "unknown",
            "bulk_bootstrap": "legal_review_required",
            "artifact_redistribution": "legal_review_required",
        },
        "systematic_use_status": "REQUIRES_REVIEW",
        "adapter_classification": "RESEARCH_ONLY / REVIEW_REQUIRED",
    },
    {
        "source_key": "hallberg_rassy",
        "source_display_name": "Hallberg-Rassy",
        "evidence_surfaces": (
            surfaces(
                "oldshop.hallberg-rassy.com",
                [
                    "/contents/en-us/d291_Hallberg-Rassy-Elvstrom-Zippack-System.html",
                    "/contents/en-us/p1378_Gelcoat_Information_Deck.html",
                ],
            )
            + surfaces("www.hallberg-rassy.com", ["/"])
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Official manufacturer/parts surfaces expose a broad list of historical and current Hallberg-Rassy model identities; official historical newsletters reference the manufacturer's Previous Models material (exact newsletter/model-list path not retained by the supplied external research pass).",
            "evidence_urls": ["https://www.hallberg-rassy.com/"],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": (
                "Historical newsletters provide specific permission to quote the newsletter with "
                "source attribution."
            ),
            "note": "That limited newsletter permission MUST NOT be generalized into an open licence for the whole manufacturer site/database; no general automated/bulk archive reuse permission found.",
            "evidence_urls": ["https://www.hallberg-rassy.com/"],
        },
        "automation_evidence": {
            "robots_or_api_status": "unknown_unretrieved",
            "note": UNRETRIEVED_AUTOMATION_NOTE
            + " The newsletter quote-with-attribution permission is a narrow redistribution "
            "permission, not a robots.txt/API/automation finding, and is not generalized here.",
        },
        "research_finding_note": (
            "Official manufacturer/parts surfaces expose a broad list of historical and current "
            "Hallberg-Rassy model identities; official historical newsletters reference the "
            "manufacturer's Previous Models material; historical newsletters provide specific "
            "permission to quote the newsletter with source attribution, but that limited newsletter "
            "permission MUST NOT be generalized into an open licence for the whole manufacturer "
            "site/database; no general automated/bulk archive reuse permission found."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "conditional",
            "production_value": "conditional",
            "automated_ingestion": "unknown",
            "bulk_bootstrap": "legal_review_required",
            "artifact_redistribution": "legal_review_required",
        },
        "systematic_use_status": "REQUIRES_REVIEW",
        "adapter_classification": "RESEARCH_ONLY / REVIEW_REQUIRED",
    },
    {
        "source_key": "seawind_catamarans",
        "source_display_name": "Seawind Catamarans",
        "evidence_surfaces": surfaces(
            "www.seawindcats.com",
            [
                "/our-catamarans",
                "/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "/benefits-of-a-catamaran/",
                "/?terms-and-privacy=yes",
            ],
        ),
        "access_evidence": {
            "public_access": "public",
            "note": "Official current model catalogue is public; official 40-year history records earlier Seawind identities including 1000, 1200, 1000XL, 1000XL2, 1250 and others.",
            "evidence_urls": [
                "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/"
            ],
        },
        "rights_evidence": {
            "terms_or_licence_evidence": None,
            "note": (
                "Site visibly exposes a 'Terms & Privacy' link, but the linked terms/privacy content "
                "could not be reliably retrieved during the ChatGPT pass; therefore its actual "
                "content is UNKNOWN and MUST NOT be guessed. No retained explicit automated/bulk "
                "permission exists."
            ),
            "evidence_urls": ["https://www.seawindcats.com/?terms-and-privacy=yes"],
        },
        "automation_evidence": {
            "robots_or_api_status": "unknown_unretrieved",
            "note": UNRETRIEVED_AUTOMATION_NOTE
            + " The site's Terms & Privacy link itself could not be reliably retrieved, so its "
            "content is recorded as unknown rather than assumed permissive or prohibitive.",
        },
        "research_finding_note": (
            "Official current model catalogue is public; official 40-year history records earlier "
            "Seawind identities including 1000, 1200, 1000XL, 1000XL2, 1250 and others; site visibly "
            "exposes a 'Terms & Privacy' link; the linked terms/privacy content could not be reliably "
            "retrieved during the ChatGPT pass; therefore its actual content is UNKNOWN and MUST NOT "
            "be guessed; no retained explicit automated/bulk permission exists."
        ),
        "use_specific_decisions": {
            "research_reference": "allowed",
            "research_lead": "allowed",
            "identity_seed": "conditional",
            "production_value": "conditional",
            "automated_ingestion": "unknown",
            "bulk_bootstrap": "legal_review_required",
            "artifact_redistribution": "legal_review_required",
        },
        "systematic_use_status": "REQUIRES_REVIEW",
        "adapter_classification": "RESEARCH_ONLY / REVIEW_REQUIRED",
    },
]


def main() -> None:
    assert len(SOURCES) == 10, f"expected 10 sources, got {len(SOURCES)}"

    records: list[dict[str, Any]] = []
    for source in SOURCES:
        record = dict(source)
        record["review_date"] = REVIEW_DATE
        record["adapter_ready_test"] = adapter_ready_test(record["use_specific_decisions"])
        # ADAPTER_READY may never be asserted without the recomputed test actually passing.
        if record["adapter_classification"] == "ADAPTER_READY":
            assert record["adapter_ready_test"]["result"] is True
        else:
            assert record["adapter_ready_test"]["result"] is False
        records.append(record)

    document = {
        "schema_version": "0020-v1",
        "generated_at": GENERATED_AT,
        "slice_id": "SLICE-0020",
        "review_date": REVIEW_DATE,
        "source_note": (
            "The ChatGPT-led external research pass performed the source-clearance research "
            "(visiting manufacturer/archive sites, reading terms/robots/licence evidence) for all "
            "ten fixed sample sources and supplied the findings transcribed here. Claude performed "
            "no independent external research; Claude's role was repository-local structural "
            "transcription into this schema, plus deterministic recomputation of the "
            "adapter_ready_test field from the transcribed use_specific_decisions."
        ),
        "sources": records,
    }

    OUT_PATH.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    adapter_ready = sum(1 for r in records if r["adapter_classification"] == "ADAPTER_READY")
    research_only = sum(
        1 for r in records if r["adapter_classification"] == "RESEARCH_ONLY / REVIEW_REQUIRED"
    )
    blocked = sum(1 for r in records if r["adapter_classification"] == "BLOCKED")

    print("SLICE-0020 archive_source_clearance.json built")
    print(f"sources={len(records)}")
    print(
        f"ADAPTER_READY={adapter_ready} RESEARCH_ONLY/REVIEW_REQUIRED={research_only} BLOCKED={blocked}"
    )


if __name__ == "__main__":
    main()
