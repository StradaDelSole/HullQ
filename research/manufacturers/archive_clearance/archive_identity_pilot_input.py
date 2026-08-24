"""SLICE-0020 bounded identity-pilot input data.

Ten source-presented model-identity lists (exactly 10 identities per source,
100 total), transcribed verbatim from the ChatGPT-led external research pass
supplied for SLICE-0020. Claude performed no independent external research to
produce these lists; see ARCHIVE_SOURCE_CLEARANCE_REPORT.md for the full
external-research-vs-repository-integration boundary statement.

Each identity retains only: model name (exactly as presented by the source),
the source surface it was found on, and the minimum discriminating context
actually available from the supplied research (hull type and any explicit
model-number/generation/variant marker already present in the name or
noted by the research pass). No broader technical specification was
harvested, and no era/context was invented beyond what the supplied research
findings state.
"""

from __future__ import annotations

from typing import Any

_MONOHULL = "monohull sailboat"
_CATAMARAN = "catamaran"

SOURCES: list[dict[str, Any]] = [
    {
        "source_key": "catalina_yachts",
        "source_display_name": "Catalina Yachts",
        "model_identities": [
            {
                "model_name": "Catalina 16.5",
                "source_surface": "https://www.catalinayachts.com/brochure-archives/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Catalina 18",
                "source_surface": "https://www.catalinayachts.com/brochure-archives/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Catalina 22 Capri",
                "source_surface": "https://www.catalinayachts.com/brochure-archives/",
                "discriminating_context": f"{_MONOHULL}; explicit variant marker 'Capri' as presented in archive listing",
            },
            {
                "model_name": "Catalina 22 Sport",
                "source_surface": "https://www.catalinayachts.com/sport-series/",
                "discriminating_context": f"{_MONOHULL}; explicit variant marker 'Sport' as presented in archive listing",
            },
            {
                "model_name": "Catalina 25",
                "source_surface": "https://www.catalinayachts.com/brochure-archives/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Catalina 27",
                "source_surface": "https://www.catalinayachts.com/brochure-archives/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Catalina 28",
                "source_surface": "https://www.catalinayachts.com/brochure-archives/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Catalina 30 MKI",
                "source_surface": "https://www.catalinayachts.com/brochure-archives/",
                "discriminating_context": f"{_MONOHULL}; explicit generation marker 'MKI' as presented in archive listing",
            },
            {
                "model_name": "Catalina 320mkII",
                "source_surface": "https://www.catalinayachts.com/brochure-archives/",
                "discriminating_context": f"{_MONOHULL}; explicit generation marker 'mkII' as presented in archive listing",
            },
            {
                "model_name": "Catalina 350mkII",
                "source_surface": "https://www.catalinayachts.com/brochure-archives/",
                "discriminating_context": f"{_MONOHULL}; explicit generation marker 'mkII' as presented in archive listing",
            },
        ],
    },
    {
        "source_key": "pearson_yachts",
        "source_display_name": "Pearson Yachts",
        "model_identities": [
            {
                "model_name": "Pearson 26",
                "source_surface": "https://www.pearsonyachts.org/pearson-sailboats.html",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Pearson 26OD",
                "source_surface": "https://www.pearsonyachts.org/models/pearson-26od.html",
                "discriminating_context": f"{_MONOHULL}; explicit variant marker 'OD' as presented on dedicated model page",
            },
            {
                "model_name": "Pearson 26W",
                "source_surface": "https://www.pearsonyachts.org/pearson-sailboats.html",
                "discriminating_context": f"{_MONOHULL}; explicit variant marker 'W' as presented in all-model table",
            },
            {
                "model_name": "Pearson 35",
                "source_surface": "https://www.pearsonyachts.org/pearson-sailboats.html",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Pearson 30",
                "source_surface": "https://www.pearsonyachts.org/pearson-sailboats.html",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Pearson 36",
                "source_surface": "https://www.pearsonyachts.org/pearson-sailboats.html",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Pearson 303",
                "source_surface": "https://www.pearsonyachts.org/pearson-sailboats.html",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Pearson 422",
                "source_surface": "https://www.pearsonyachts.org/pearson-sailboats.html",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Pearson 385",
                "source_surface": "https://www.pearsonyachts.org/pearson-sailboats.html",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Pearson 36-2",
                "source_surface": "https://www.pearsonyachts.org/pearson-sailboats.html",
                "discriminating_context": f"{_MONOHULL}; explicit generation marker '-2' as presented in all-model table",
            },
        ],
    },
    {
        "source_key": "oyster_yachts",
        "source_display_name": "Oyster Yachts",
        "model_identities": [
            {
                "model_name": "Oyster 625",
                "source_surface": "https://oysteryachts.com/heritage-yachts/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Oyster 62",
                "source_surface": "https://oysteryachts.com/heritage-yachts/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Oyster 61",
                "source_surface": "https://oysteryachts.com/heritage-yachts/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Oyster 575",
                "source_surface": "https://oysteryachts.com/heritage-yachts/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Oyster 56",
                "source_surface": "https://oysteryachts.com/heritage-yachts/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Oyster 545",
                "source_surface": "https://oysteryachts.com/heritage-yachts/oyster-545/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented, dedicated model page",
            },
            {
                "model_name": "Oyster 54",
                "source_surface": "https://oysteryachts.com/heritage-yachts/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Oyster 53",
                "source_surface": "https://oysteryachts.com/heritage-yachts/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Oyster 495",
                "source_surface": "https://oysteryachts.com/heritage-yachts/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Oyster 49",
                "source_surface": "https://oysteryachts.com/heritage-yachts/",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
        ],
    },
    {
        "source_key": "westerly_marine",
        "source_display_name": "Westerly Marine / Westerly Owners Association",
        "model_identities": [
            {
                "model_name": "Berwick",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; name preserved exactly as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
            {
                "model_name": "Centaur",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; name preserved exactly as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
            {
                "model_name": "Chieftain",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; name preserved exactly as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
            {
                "model_name": "Cirrus",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; name preserved exactly as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
            {
                "model_name": "Conway",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; name preserved exactly as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
            {
                "model_name": "Corsair 36",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; explicit model-number marker '36' as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
            {
                "model_name": "Falcon 34",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; explicit model-number marker '34' as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
            {
                "model_name": "Fulmar",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; name preserved exactly as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
            {
                "model_name": "Griffon 26",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; explicit model-number marker '26' as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
            {
                "model_name": "Konsort",
                "source_surface": "https://wiki.westerly-owners.co.uk/index.php?title=Main_Page",
                "discriminating_context": f"{_MONOHULL}; name preserved exactly as presented on the owners-association wiki, manufacturer-prefix not added per slice rule",
            },
        ],
    },
    {
        "source_key": "beneteau",
        "source_display_name": "Bénéteau",
        "model_identities": [
            {
                "model_name": "First 18",
                "source_surface": "https://www.beneteau.com/en-us/first-1977-1983/first-18",
                "discriminating_context": f"{_MONOHULL}; sourced from heritage era index labeled 'First 1977-1983', dedicated model page",
            },
            {
                "model_name": "First 22",
                "source_surface": "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983",
                "discriminating_context": f"{_MONOHULL}; sourced from heritage era index labeled 'First 1977-1983'",
            },
            {
                "model_name": "First 24",
                "source_surface": "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983",
                "discriminating_context": f"{_MONOHULL}; sourced from heritage era index labeled 'First 1977-1983'",
            },
            {
                "model_name": "First 25",
                "source_surface": "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983",
                "discriminating_context": f"{_MONOHULL}; sourced from heritage era index labeled 'First 1977-1983'",
            },
            {
                "model_name": "First 26",
                "source_surface": "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983",
                "discriminating_context": f"{_MONOHULL}; sourced from heritage era index labeled 'First 1977-1983'; exact label 'First 26' preserved, no manufacturer prefix added or stripped per slice overlap-guard rule",
            },
            {
                "model_name": "First 27",
                "source_surface": "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983",
                "discriminating_context": f"{_MONOHULL}; sourced from heritage era index labeled 'First 1977-1983'",
            },
            {
                "model_name": "First 28",
                "source_surface": "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983",
                "discriminating_context": f"{_MONOHULL}; sourced from heritage era index labeled 'First 1977-1983'",
            },
            {
                "model_name": "First 29",
                "source_surface": "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983",
                "discriminating_context": f"{_MONOHULL}; sourced from heritage era index labeled 'First 1977-1983'",
            },
            {
                "model_name": "First 32",
                "source_surface": "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983",
                "discriminating_context": f"{_MONOHULL}; listed alongside the 'First 1977-1983' era index; per-model era not independently confirmed beyond page label",
            },
            {
                "model_name": "First 38",
                "source_surface": "https://www.beneteau.com/en-us/heritage-sailing-yachts/first-1977-1983",
                "discriminating_context": f"{_MONOHULL}; listed alongside the 'First 1977-1983' era index; per-model era not independently confirmed beyond page label",
            },
        ],
    },
    {
        "source_key": "wauquiez",
        "source_display_name": "Wauquiez",
        "model_identities": [
            {
                "model_name": "CENTURION 32",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; explicit range name 'CENTURION' as presented on historical timeline",
            },
            {
                "model_name": "PRETORIEN",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; name preserved exactly as presented on historical timeline",
            },
            {
                "model_name": "PILOT SALOON 60",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; explicit range name 'PILOT SALOON' as presented on historical timeline",
            },
            {
                "model_name": "PILOT SALOON 54",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; explicit range name 'PILOT SALOON' as presented on historical timeline",
            },
            {
                "model_name": "CENTURION 41S",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; explicit range name 'CENTURION' and variant suffix 'S' as presented on historical timeline",
            },
            {
                "model_name": "CENTURION 48S",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; explicit range name 'CENTURION' and variant suffix 'S' as presented on historical timeline",
            },
            {
                "model_name": "PILOT SALOON 48",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; explicit range name 'PILOT SALOON' as presented on historical timeline",
            },
            {
                "model_name": "PILOT SALOON 43",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; explicit range name 'PILOT SALOON' as presented on historical timeline",
            },
            {
                "model_name": "PILOT SALOON 40",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; explicit range name 'PILOT SALOON' as presented on historical timeline",
            },
            {
                "model_name": "CENTURION 40S",
                "source_surface": "https://www.wauquiez.com/une-grande-histoire/",
                "discriminating_context": f"{_MONOHULL}; explicit range name 'CENTURION' and variant suffix 'S' as presented on historical timeline",
            },
        ],
    },
    {
        "source_key": "elan",
        "source_display_name": "Elan",
        "model_identities": [
            {
                "model_name": "Elan 31",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Elan 33",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Elan 39",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Elan 43",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Elan 35 Performance",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; explicit variant marker 'Performance' as presented",
            },
            {
                "model_name": "Elan 333",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Elan 340",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Impression 344",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; distinct sub-line name 'Impression' rather than 'Elan' prefix, as presented",
            },
            {
                "model_name": "Elan 350",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Elan E3",
                "source_surface": "https://www.elan-yachts.com/en/previous-models",
                "discriminating_context": f"{_MONOHULL}; listed on the 'Previous Models' archive surface despite an 'E3' designation that may denote a more recent production line; flagged as an identity-timeline hazard, not resolved here",
            },
        ],
    },
    {
        "source_key": "cantiere_del_pardo_grand_soleil",
        "source_display_name": "Cantiere del Pardo / Grand Soleil",
        "model_identities": [
            {
                "model_name": "Grand Soleil 34",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; full 'Grand Soleil' name form as presented on heritage history page",
            },
            {
                "model_name": "GS 35",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; abbreviated 'GS' name form as presented on heritage history page, not expanded per slice rule",
            },
            {
                "model_name": "GS 41",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; abbreviated 'GS' name form as presented on heritage history page, not expanded per slice rule",
            },
            {
                "model_name": "GS 39",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; abbreviated 'GS' name form as presented on heritage history page, not expanded per slice rule",
            },
            {
                "model_name": "GS 343",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; abbreviated 'GS' name form as presented on heritage history page, not expanded per slice rule",
            },
            {
                "model_name": "GS 46",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; abbreviated 'GS' name form as presented on heritage history page, not expanded per slice rule",
            },
            {
                "model_name": "GS 42",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; abbreviated 'GS' name form as presented on heritage history page, not expanded per slice rule",
            },
            {
                "model_name": "GS 45",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; abbreviated 'GS' name form as presented on heritage history page, not expanded per slice rule",
            },
            {
                "model_name": "GS 52",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; abbreviated 'GS' name form as presented on heritage history page, not expanded per slice rule",
            },
            {
                "model_name": "GS 40",
                "source_surface": "https://old2.grandsoleil.net/history/",
                "discriminating_context": f"{_MONOHULL}; abbreviated 'GS' name form as presented on heritage history page, not expanded per slice rule",
            },
        ],
    },
    {
        "source_key": "hallberg_rassy",
        "source_display_name": "Hallberg-Rassy",
        "model_identities": [
            {
                "model_name": "Hallberg-Rassy 29",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
            {
                "model_name": "Hallberg-Rassy 31",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
            {
                "model_name": "Hallberg-Rassy 310",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
            {
                "model_name": "Hallberg-Rassy 34",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
            {
                "model_name": "Hallberg-Rassy 340",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
            {
                "model_name": "Hallberg-Rassy 342",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
            {
                "model_name": "Hallberg-Rassy 352",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
            {
                "model_name": "Hallberg-Rassy 372",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
            {
                "model_name": "Hallberg-Rassy 40",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
            {
                "model_name": "Hallberg-Rassy 412",
                "source_surface": "https://www.hallberg-rassy.com/",
                "discriminating_context": f"{_MONOHULL}; exact discovery path not retained by the supplied external research pass beyond the manufacturer host and referenced historical-newsletter/Previous-Models material; no additional generation marker",
            },
        ],
    },
    {
        "source_key": "seawind_catamarans",
        "source_display_name": "Seawind Catamarans",
        "model_identities": [
            {
                "model_name": "Seawind 1600",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Seawind 1370",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Seawind 1270",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Seawind 1170",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Seawind 1160XL",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; explicit variant marker 'XL' as presented",
            },
            {
                "model_name": "Seawind 1160 Resort",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; explicit variant marker 'Resort' as presented",
            },
            {
                "model_name": "Seawind 1000",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Seawind 1200",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; no additional generation/variant marker beyond model number as presented",
            },
            {
                "model_name": "Seawind 1000XL",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; explicit variant marker 'XL' as presented",
            },
            {
                "model_name": "Seawind 1250",
                "source_surface": "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
                "discriminating_context": f"{_CATAMARAN}; no additional generation/variant marker beyond model number as presented",
            },
        ],
    },
]
