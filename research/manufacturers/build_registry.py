#!/usr/bin/env python3
"""Build the SLICE-0019 non-canonical manufacturer research registry.

The generator keeps the five recovered raw batches as the detailed evidence
base, applies the independent REVIEW-001..006 decisions, appends the 24
independently researched RESEARCH-007..009 records, validates the result, and
writes registry.json. The removable temporary_external_reference directory is
never read.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import jsonschema
from archive_surface import recognized_archive_surface_count

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "checkpoint" / "raw"
OUT = ROOT / "registry.json"
SCHEMA = ROOT / "registry_schema.json"
STAMP = "2026-08-23T00:00:00Z"

RAW_FILES = [
    "batch_a_north_america.json",
    "batch_b_uk_ireland.json",
    "batch_c_france_benelux.json",
    "batch_d_germanic_eastern_europe.json",
    "batch_e_nordics.json",
]

# All original needs_review records except Columbia were independently reviewed
# and resolved. Columbia remains review-bound because the recovered record
# collapses the original manufacturer and a later revival.
REVIEWED_VERIFIED = {
    "Marlow-Hunter",
    "Pacific Seacraft",
    "Performance Cruising (Gemini Catamarans)",
    "MacGregor Yacht Corporation",
    "Alerion Yachts",
    "Morgan Yachts",
    "Ericson Yachts",
    "Islander Yachts",
    "Moody",
    "Marine Projects (Plymouth) Ltd",
    "Sadler Yachts",
    "Rustler Yachts",
    "Bowman Yachts",
    "Northshore Yachts",
    "Southerly",
    "Discovery Yachts",
    "Cornish Crabbers",
    "Fountaine Pajot",
    "Lagoon",
    "CNB (Construction Navale Bordeaux)",
    "Wauquiez",
    "Gibert Marine (Gib'Sea)",
    "Kelt (Kelt Marine)",
    "Kirié (Feeling brand)",
    "Fora Marine (RM Yachts)",
    "ETAP Yachting",
    "Victoire Jachtbouw",
    "AD Boats d.o.o. (Salona Yachts)",
    "Delphia Yachts",
    "Ostróda Yacht Sp. z o.o.",
    "Antila Yachts",
    "Northman (Maxus Yachts brand)",
    "Balt-Yacht",
    "Schöchl Yachtbau (Sunbeam Watersports GmbH)",
    "AVAR-YACHT, s.r.o.",
    "Najad Yachts",
    "Maxi Yachts",
    "Nauticat Yachts",
    "Finngulf Yachts",
    "Oy Fiskars Ab Boatyard (Finnsailer)",
    "Bringsværd Boat Yard",
    "Fjord Plast AS",
}

# Verified relationship/brand records that must not inflate the strict
# manufacturer/yard floor.
BRAND_CONTEXT_ONLY = {
    "J/Boats",
    "Freedom Yachts",
    "Alerion Yachts",
    "Moody",
    "Bowman Yachts",
    "Southerly",
    "Lagoon",
    "Maxi Yachts",
}

STATUS_PATCH = {
    "Marlow-Hunter": "unknown",
    "Performance Cruising (Gemini Catamarans)": "historical",
    "MacGregor Yacht Corporation": "defunct",
    "Alerion Yachts": "unknown",
    "Morgan Yachts": "acquired",
    "Ericson Yachts": "defunct",
    "Islander Yachts": "defunct",
    "Moody": "active",
    "Marine Projects (Plymouth) Ltd": "renamed",
    "Sadler Yachts": "defunct",
    "Rustler Yachts": "active",
    "Bowman Yachts": "unknown",
    "Northshore Yachts": "defunct",
    "Southerly": "unknown",
    "Discovery Yachts": "defunct",
    "Cornish Crabbers": "historical",
    "Fountaine Pajot": "active",
    "Lagoon": "active",
    "CNB (Construction Navale Bordeaux)": "active",
    "Wauquiez": "active",
    "Gibert Marine (Gib'Sea)": "historical",
    "Kelt (Kelt Marine)": "historical",
    "Kirié (Feeling brand)": "historical",
    "Fora Marine (RM Yachts)": "historical",
    "ETAP Yachting": "unknown",
    "Victoire Jachtbouw": "defunct",
    "AD Boats d.o.o. (Salona Yachts)": "unknown",
    "Delphia Yachts": "acquired",
    "Ostróda Yacht Sp. z o.o.": "active",
    "Antila Yachts": "active",
    "Northman (Maxus Yachts brand)": "active",
    "Balt-Yacht": "active",
    "Schöchl Yachtbau (Sunbeam Watersports GmbH)": "active",
    "AVAR-YACHT, s.r.o.": "active",
    "Najad Yachts": "active",
    "Maxi Yachts": "unknown",
    "Nauticat Yachts": "defunct",
    "Finngulf Yachts": "unknown",
    "Oy Fiskars Ab Boatyard (Finnsailer)": "historical",
    "Bringsværd Boat Yard": "defunct",
    "Fjord Plast AS": "historical",
}

ERA_PATCH = {
    "Marine Projects (Plymouth) Ltd": (1965, None, "exact"),
    "Gibert Marine (Gib'Sea)": (1972, 1996, "estimated"),
    "Kelt (Kelt Marine)": (1974, 1989, "estimated"),
    "Kirié (Feeling brand)": (1980, 2000, "estimated"),
    "Fora Marine (RM Yachts)": (1989, 2020, "estimated"),
    "Victoire Jachtbouw": (1934, 2005, "estimated"),
    "AD Boats d.o.o. (Salona Yachts)": (2001, None, "estimated"),
    "Antila Yachts": (None, None, "unknown"),
    "Najad Yachts": (1971, None, "exact"),
    "Nauticat Yachts": (1961, 2018, "exact"),
    "Finngulf Yachts": (1981, None, "exact"),
    "Oy Fiskars Ab Boatyard (Finnsailer)": (1970, 1980, "estimated"),
    "Bringsværd Boat Yard": (1956, 1984, "estimated"),
    "Fjord Plast AS": (1960, 1980, "estimated"),
}

KIND_PATCH = {
    "J/Boats": ["brand"],
    "Freedom Yachts": ["brand"],
    "Alerion Yachts": ["brand"],
    "Moody": ["brand"],
    "Bowman Yachts": ["brand"],
    "Southerly": ["brand"],
    "Lagoon": ["brand"],
    "Maxi Yachts": ["brand"],
    "Marine Projects (Plymouth) Ltd": ["manufacturer", "yard", "legal_organization"],
    "Northshore Yachts": ["manufacturer", "yard"],
    "Discovery Yachts": ["manufacturer", "yard", "legal_organization"],
    "CNB (Construction Navale Bordeaux)": ["manufacturer", "yard", "legal_organization"],
    "Gibert Marine (Gib'Sea)": ["manufacturer", "yard"],
    "Kirié (Feeling brand)": ["manufacturer", "yard"],
    "Fora Marine (RM Yachts)": ["manufacturer", "yard"],
    "Ostróda Yacht Sp. z o.o.": ["manufacturer", "yard", "legal_organization"],
    "Northman (Maxus Yachts brand)": ["manufacturer", "yard"],
    "Balt-Yacht": ["manufacturer", "yard"],
    "Schöchl Yachtbau (Sunbeam Watersports GmbH)": ["manufacturer", "yard", "legal_organization"],
    "Nauticat Yachts": ["manufacturer", "yard", "brand"],
    "Oy Fiskars Ab Boatyard (Finnsailer)": ["manufacturer", "yard"],
    "Fjord Plast AS": ["manufacturer", "yard"],
}

NOTES = {
    "J/Boats": "Verified brand/design/marketing context; physical manufacture is assigned to contract builders such as TPI.",
    "Freedom Yachts": "Verified brand/program context; preserved evidence states TPI manufactured the boats.",
    "Alerion Yachts": "Verified brand/program context; Holby Marine, TPI, US Watercraft and Eastman were separate physical builders.",
    "Columbia Yachts": "Original manufacturer and 2001 revival remain collapsed in one recovered record; lineage must be separated before verification.",
    "Moody": "Verified brand context; Marine Projects historically and HanseYachts later are modeled as physical manufacturers.",
    "Marine Projects (Plymouth) Ltd": "Historical sailboat manufacturer verified; the legal company continued through rename to Princess Yachts rather than disappearing.",
    "Bowman Yachts": "Verified brand context; production occurred through separate legal manufacturers.",
    "Southerly": "Verified brand context; Northshore and Discovery are modeled as physical builders.",
    "Lagoon": "Verified active brand/program; physical manufacture is within Groupe Bénéteau/CNB facilities.",
    "Victoire Jachtbouw": "Original yard lineage traces to Cor Vader's 1934 Jachtwerf Victoria; Dick Koopmans was principal designer, not founder. Later restarts are successors.",
    "Delphia Yachts": "Historical Polish series manufacturer verified; weak Sportlake alias is not relied upon.",
    "Northman (Maxus Yachts brand)": "Northman is the physical manufacturer/yard; Maxus is its sailing-yacht brand.",
    "Najad Yachts": "Active Swedish manufacturer/yard verified; prior combined Najad+Maxi output is not used as a Najad-only yield.",
    "Maxi Yachts": "Verified production brand context; physical builders are modeled separately.",
    "Nauticat Yachts": "Record covers the original Finnish Siltala/Nauticat manufacturer through 2018; the 2022 Latvian revival is a separate successor.",
    "Bringsværd Boat Yard": "Direct family/yard history confirms continued yard activity to 1984; 1968 marks only an earlier production phase.",
    "Fjord Plast AS": "Historical Norwegian manufacturer/yard kept distinct from the current German powerboat-only FJORD brand.",
}

MODEL_YIELD_PATCH = {
    "Najad Yachts": {
        "value": None,
        "basis": "unknown",
        "notes": "Prior combined Najad+Maxi output is not a Najad-only manufacturer yield.",
    },
    "Kelt (Kelt Marine)": {
        "value": None,
        "basis": "unknown",
        "notes": "Conflicting secondary lifetime-output figures are not normalized.",
    },
    "Fountaine Pajot": {
        "value": 4000,
        "basis": "estimated",
        "notes": "Official company material reports roughly 4,000 Fountaine Pajot cruising catamarans; group totals are excluded.",
    },
    "Bringsværd Boat Yard": {
        "value": 1200,
        "basis": "estimated",
        "notes": "Direct family history reports roughly 1,200 BB11s; other series are not collapsed into a false exact lifetime total.",
    },
    "Islander Yachts": {
        "value": None,
        "basis": "unknown",
        "notes": "Earlier weak cumulative-unit estimate is not retained as normalized yield.",
    },
}

ALIAS_PATCH = {
    "Delphia Yachts": [
        "Delphia Yachts Kot sp. j.",
        "Stocznia Jachtowa Delphia sp. z o.o.",
    ],
}
CLEAR_OFFICIAL_SITE = {"Delphia Yachts"}

# Records whose retained non-null numeric yield figure describes discoverable
# distinct model identities (e.g. "5 current sailboat models"), not a
# cumulative production-unit/hull count. Every other non-null figure in the
# recovered/independent research is a production-unit claim (e.g. "more than
# 85,000 Catalinas on the water") and is routed to production_unit_count
# instead. This mapping was derived by reading each record's retained
# model_yield_estimate.notes text; no numeric value is reinterpreted.
MODEL_IDENTITY_YIELD_NAMES = {
    "Oyster Yachts",
    "Colvic Marine",
    "Dehler Yachts",
    "Seascape d.o.o.",
    "AD Boats d.o.o. (Salona Yachts)",
    "Ostróda Yacht Sp. z o.o.",
    "Antila Yachts",
    "Schöchl Yachtbau (Sunbeam Watersports GmbH)",
    "AVAR-YACHT, s.r.o.",
}


def split_yield(name: str, yield_estimate: dict) -> tuple[dict, dict]:
    """Split the legacy mixed model_yield_estimate into two unambiguous fields.

    Returns (model_identity_yield, production_unit_count). No existing numeric
    value is changed; each retained value is routed to exactly one of the two
    fields based on what its own notes text describes, and the other field is
    left explicitly unknown.
    """
    if yield_estimate["value"] is None:
        unknown = dict(yield_estimate)
        return unknown, dict(unknown)
    if name in MODEL_IDENTITY_YIELD_NAMES:
        identity = dict(yield_estimate)
        units = {
            "value": None,
            "basis": "unknown",
            "notes": "No normalized cumulative production-unit count retained; "
            "the retained figure describes discoverable model identities, not production units.",
        }
        return identity, units
    units = dict(yield_estimate)
    identity = {
        "value": None,
        "basis": "unknown",
        "notes": "No normalized discoverable model-identity count retained; "
        "the retained figure is a cumulative production-unit count (see production_unit_count).",
    }
    return identity, units


# Evidence-backed relationships for the 24 independently researched
# RESEARCH-007..009 records, drawn only from those retained packets. Records
# not listed here have no evidence-backed relationship and keep relationships: [].
NEW_RELATIONSHIPS = {
    "Cantiere del Pardo": [
        {
            "type": "other",
            "related_name": "Grand Soleil",
            "evidence_note": "Grand Soleil is the sailing-yacht brand/product lineage associated with the "
            "physical/legal Cantiere del Pardo yard, not a separate yard.",
            "source_url": "https://cantieredelpardo.com/it/the-yard/our-heritage/",
        }
    ],
    "Comar Yachts / Sipla": [
        {
            "type": "formerly_known_as",
            "related_name": "Sipla",
            "evidence_note": "The business began in Forlì in 1961 under the name Sipla, producing fiberglass "
            "Flying Juniors, and changed its name to Comar after roughly ten years.",
            "source_url": "https://www.comaryachts.it/en/history/",
        },
        {
            "type": "other",
            "related_name": "Comet",
            "evidence_note": "Comet is a model/range brand lineage of the Comar yard (the Comet 910 alone was "
            "produced in almost 1,000 units), not a separate manufacturer.",
            "source_url": "https://www.comaryachts.it/en/history/",
        },
    ],
    "Alpa": [
        {
            "type": "other",
            "related_name": "Cantiere Zuanelli",
            "evidence_note": "Zuanelli's official history states that in 1975 it acquired manufacturing "
            "know-how from the Alpa operation in Offanengo, corroborating Alpa's industrial sailboat-building role.",
            "source_url": "https://zuanelli.it/chi-siamo/",
        }
    ],
    "Cantiere Zuanelli": [
        {
            "type": "other",
            "related_name": "Alpa",
            "evidence_note": "In 1975 the yard acquired manufacturing know-how from the Alpa operation in "
            "Offanengo and specialized in fiberglass sailing-yacht construction.",
            "source_url": "https://zuanelli.it/chi-siamo/",
        }
    ],
    "Ta Yang Yacht Building Co., Ltd.": [
        {
            "type": "other",
            "related_name": "Tayana",
            "evidence_note": "Tayana is the product/brand lineage of the Ta Yang physical manufacturer, not a "
            "separate yard.",
            "source_url": "https://www.taiwan-yacht.com.tw/en-members.html",
        }
    ],
    "Ta Shing Yacht Building": [
        {
            "type": "predecessor",
            "related_name": "Shing Sheng boatyard",
            "evidence_note": "A predecessor boatbuilding lineage under Shing Sheng is commonly traced to 1957; "
            "modeled separately from the current legal entity's 1977 registration rather than backdating it.",
            "source_url": "https://findbiz.nat.gov.tw/fts/company/69559634?fhl=en",
        }
    ],
    "Queen Long Marine": [
        {
            "type": "other",
            "related_name": "Hylas",
            "evidence_note": "Hylas' own company material states Queen Long Marine is the shipyard, founder and "
            "owner of the Hylas brand.",
            "source_url": "https://www.hylasyachts.com/about/",
        }
    ],
    "Fuji Yacht Builders": [
        {
            "type": "predecessor",
            "related_name": "Far East Yachts / Far East Boat Ltd.",
            "evidence_note": "Former Far East/TOA personnel established Fuji Yacht Builders; the yards remain "
            "distinct entities despite overlapping personnel, site and mould history.",
            "source_url": "https://www.fujiyachts.net/history/history.html",
        }
    ],
    "Far East Yachts / Far East Boat Ltd.": [
        {
            "type": "successor",
            "related_name": "Fuji Yacht Builders",
            "evidence_note": "Former Far East/TOA personnel later established Fuji Yacht Builders; the yards "
            "remain distinct entities despite overlapping personnel, site and mould history.",
            "source_url": "https://www.fujiyachts.net/history/takao.html",
        }
    ],
    "Bashford Boats / Bashford International": [
        {
            "type": "production_transferred_to",
            "related_name": "AD Boats d.o.o. (Salona Yachts)",
            "evidence_note": "Sydney Yachts' own company page states that since 2013 Sydney Yachts have been "
            "built at AD Boats in Croatia; the Australian Bashford/Sydney yard history remains a separate "
            "physical-manufacturer lineage.",
            "source_url": "https://www.sydneyyachts.com/company/sydney-yachts.html",
        }
    ],
    "Robertson & Caine": [
        {
            "type": "acquired_by",
            "related_name": "Vox Ventures / PPF",
            "evidence_note": "Corporate ownership relationship; does not alter Robertson & Caine's distinct "
            "physical-manufacturer identity.",
            "source_url": "https://www.robertsonandcaine.com/overview.html",
        }
    ],
    "Cavalier Yachts": [
        {
            "type": "successor",
            "related_name": "Export Yachts Ltd",
            "evidence_note": "The original company was damaged by the 1979 New Zealand sales-tax shock and "
            "later entered receivership; subsequent Export Yachts Ltd activity is a successor/continuation "
            "relationship, not an alias.",
            "source_url": "https://www.petersmith.net.nz/about/peter.php",
        }
    ],
}

# Losslessly retain two evidenced production-era facts from the RESEARCH-008
# packet that the original registry integration dropped to unknown/unknown.
NEW_ERA_OVERRIDE = {
    # "The present legal entity registered in 1977" (RESEARCH-008 #3).
    "Ta Shing Yacht Building": (1977, None, "exact"),
    # "Launched the Fuji production-yacht line beginning ... in the early
    # 1970s" through "ceased operations around the turn of the 1980s"
    # (RESEARCH-008 #7).
    "Fuji Yacht Builders": (1970, 1980, "estimated"),
}

# New records: name, aliases, kinds, country, region, status, start, end, basis,
# current site, heritage surface, source URLs, yield value/basis/notes, ambiguity.
NEW = [
    (
        "Cantiere del Pardo",
        ["Grand Soleil"],
        ["manufacturer", "yard"],
        "Italy",
        "Southern Europe",
        "active",
        1973,
        None,
        "exact",
        "https://cantieredelpardo.com/",
        "https://cantieredelpardo.com/it/the-yard/our-heritage/",
        [
            "https://cantieredelpardo.com/company/our-values/",
            "https://cantieredelpardo.com/it/the-yard/our-heritage/",
        ],
        5000,
        "estimated",
        "Company material states more than 5,000 boats launched; GS34 alone 290.",
        None,
    ),
    (
        "Comar Yachts / Sipla",
        ["Comar Yachts", "Sipla", "Comet"],
        ["manufacturer", "yard"],
        "Italy",
        "Southern Europe",
        "active",
        1961,
        None,
        "exact",
        "https://www.comaryachts.it/en/history/",
        "https://www.comaryachts.it/en/history/",
        ["https://www.comaryachts.it/en/history/"],
        5000,
        "estimated",
        "Official history gives several-thousand cumulative output; Comet 910 alone approached 1,000.",
        None,
    ),
    (
        "Solaris Yachts",
        [],
        ["manufacturer", "yard"],
        "Italy",
        "Southern Europe",
        "active",
        1974,
        None,
        "exact",
        "https://www.solarisyachts.com/",
        "https://www.solarisyachts.com/en/milestones/",
        ["https://www.solarisyachts.com/en/milestones/"],
        None,
        "unknown",
        "Current/historical repeated model series verified.",
        None,
    ),
    (
        "Alpa",
        [],
        ["manufacturer", "yard"],
        "Italy",
        "Southern Europe",
        "defunct",
        1956,
        1979,
        "estimated",
        None,
        "https://www.alpahistorical.org/storia-del-cantiere.html",
        ["https://www.alpahistorical.org/storia-del-cantiere.html"],
        None,
        "unknown",
        "Historical repeated production verified.",
        None,
    ),
    (
        "Cantiere Zuanelli",
        [],
        ["manufacturer", "yard"],
        "Italy",
        "Southern Europe",
        "active",
        1972,
        None,
        "exact",
        "https://zuanelli.it/",
        "https://zuanelli.it/chi-siamo/",
        ["https://zuanelli.it/chi-siamo/"],
        None,
        "unknown",
        "Repeated cruising-yacht model line verified.",
        None,
    ),
    (
        "Italia Yachts",
        [],
        ["manufacturer", "yard"],
        "Italy",
        "Southern Europe",
        "active",
        2011,
        None,
        "exact",
        "https://www.italiayachtsinternational.com/",
        "https://www.italiayachtsinternational.com/en_en/azienda/cantiere/",
        ["https://www.italiayachtsinternational.com/en_en/azienda/cantiere/"],
        None,
        "unknown",
        "Current repeated performance-cruiser production verified.",
        None,
    ),
    (
        "North Wind Yachts",
        [],
        ["manufacturer", "yard"],
        "Spain",
        "Southern Europe",
        "historical",
        1973,
        None,
        "estimated",
        None,
        None,
        [
            "https://www.devalk.nl/en/yachtbrokerage/252093/NORTH-WIND-47.html",
            "https://barcosnautica.com/en/embarcaciones/north-wind-47",
        ],
        None,
        "unknown",
        "Historical repeated cruising-yacht production verified.",
        "Current corporate continuity remains unknown.",
    ),
    (
        "Belliure",
        [],
        ["manufacturer", "yard"],
        "Spain",
        "Southern Europe",
        "defunct",
        1953,
        2017,
        "exact",
        "https://www.belliure.com/",
        "https://www.belliure.com/pa-historia-536-441.html",
        [
            "https://www.belliure.com/pa-historia-536-441.html",
            "https://www.belliure.com/pa-belliure-35-endurance-536-719-es.html",
        ],
        170,
        "estimated",
        "Official history states more than 170 GRP boats; Endurance 35 reached 160 units.",
        None,
    ),
    (
        "Cheoy Lee Shipyards",
        [],
        ["manufacturer", "yard"],
        "Hong Kong",
        "Asia-Pacific",
        "active",
        1957,
        1990,
        "estimated",
        "https://cheoylee.com/",
        "https://cheoylee.com/heritage/",
        ["https://cheoylee.com/heritage/"],
        None,
        "unknown",
        "Historic production-yacht output verified; Lion 35 alone exceeded 90 across wood and GRP.",
        "Company remains active; qualifying sailboat production is historical and current construction is centered in Zhuhai, China.",
    ),
    (
        "Ta Yang Yacht Building Co., Ltd.",
        ["Tayana"],
        ["manufacturer", "yard"],
        "Taiwan",
        "Asia-Pacific",
        "defunct",
        1972,
        2020,
        "exact",
        None,
        None,
        ["https://findcompany.com.tw/TA%20YANG%20YACHT%20BUILDING%20CO.%2C%20LTD."],
        1400,
        "estimated",
        "Industry sources report more than 1,400 Ta Yang/Tayana cruisers.",
        None,
    ),
    (
        "Ta Shing Yacht Building",
        [],
        ["manufacturer", "yard"],
        "Taiwan",
        "Asia-Pacific",
        "active",
        None,
        None,
        "unknown",
        None,
        None,
        ["https://findbiz.nat.gov.tw/fts/company/69559634?fhl=en"],
        None,
        "unknown",
        "Extensive repeated OEM and own-line sailboat construction verified.",
        None,
    ),
    (
        "Queen Long Marine",
        ["Hylas"],
        ["manufacturer", "yard"],
        "Taiwan",
        "Asia-Pacific",
        "active",
        None,
        None,
        "unknown",
        "https://www.hylasyachts.com/about/",
        None,
        ["https://www.hylasyachts.com/about/"],
        None,
        "unknown",
        "Current repeated Hylas production verified.",
        None,
    ),
    (
        "New Japan Yacht",
        [],
        ["manufacturer", "yard"],
        "Japan",
        "Asia-Pacific",
        "active",
        1969,
        None,
        "exact",
        "https://www.njy.co.jp/",
        None,
        ["https://www.njy.co.jp/company/"],
        800,
        "estimated",
        "Company states more than 800 yachts built.",
        None,
    ),
    (
        "Yamaha Motor marine yacht activity",
        [],
        ["manufacturer"],
        "Japan",
        "Asia-Pacific",
        "historical",
        1970,
        1990,
        "estimated",
        "https://www.yamaha-motor.co.jp/marine/history/products-history/1970/",
        None,
        ["https://www.yamaha-motor.co.jp/marine/history/products-history/1970/"],
        None,
        "unknown",
        "Broad multi-model historical production series verified.",
        None,
    ),
    (
        "Fuji Yacht Builders",
        [],
        ["manufacturer", "yard"],
        "Japan",
        "Asia-Pacific",
        "historical",
        None,
        None,
        "unknown",
        None,
        None,
        ["https://www.fujiyachts.net/history/history.html"],
        200,
        "estimated",
        "Historical sources report more than 200 boats across the Fuji series.",
        None,
    ),
    (
        "Far East Yachts / Far East Boat Ltd.",
        [],
        ["manufacturer", "yard"],
        "Japan",
        "Asia-Pacific",
        "historical",
        1958,
        1971,
        "estimated",
        None,
        None,
        ["https://www.fujiyachts.net/history/takao.html"],
        None,
        "unknown",
        "Historical repeated Mariner-series production verified.",
        None,
    ),
    (
        "McConaghy Boats",
        [],
        ["manufacturer", "yard"],
        "Australia",
        "Asia-Pacific",
        "active",
        1967,
        None,
        "exact",
        "https://mcconaghyboats.com/",
        "https://mcconaghyboats.com/our-story/",
        ["https://mcconaghyboats.com/our-story/", "https://mcconaghyboats.com/facilities/"],
        150,
        "estimated",
        "Company states a fleet of more than 150 yachts 30 ft and above, excluding many smaller series.",
        None,
    ),
    (
        "Bashford Boats / Bashford International",
        ["Sydney Yachts"],
        ["manufacturer", "yard"],
        "Australia",
        "Asia-Pacific",
        "historical",
        1980,
        2013,
        "estimated",
        None,
        None,
        ["https://www.sydneyyachts.com/company/sydney-yachts.html"],
        None,
        "unknown",
        "Repeated J/Boat, Etchells and Sydney production programs verified.",
        "Post-2013 Sydney Yachts production transferred to AD Boats in Croatia.",
    ),
    (
        "Seawind Catamarans",
        [],
        ["manufacturer", "yard", "brand"],
        "Australia",
        "Asia-Pacific",
        "active",
        1982,
        None,
        "exact",
        "https://www.seawindcats.com/",
        "https://www.seawindcats.com/about-us/",
        [
            "https://www.seawindcats.com/about-us/",
            "https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/",
        ],
        350,
        "estimated",
        "Seawind 24 alone exceeded 350 hulls.",
        "Current primary production is in Vietnam with additional production in Türkiye.",
    ),
    (
        "Robertson & Caine",
        [],
        ["manufacturer", "yard"],
        "South Africa",
        "Rest of World",
        "active",
        1991,
        None,
        "exact",
        "https://www.robertsonandcaine.com/",
        None,
        [
            "https://www.robertsonandcaine.com/overview.html",
            "https://www.robertsonandcaine.com/achievements.html",
        ],
        3132,
        "estimated",
        "Official achievements page reports more than 3,132 catamarans through April 2026.",
        None,
    ),
    (
        "St Francis Marine",
        [],
        ["manufacturer", "yard"],
        "South Africa",
        "Rest of World",
        "active",
        1988,
        None,
        "exact",
        "https://stfranciscatamarans.com/",
        "https://www.stfranciscatamarans.com/our-history",
        ["https://stfranciscatamarans.com/", "https://www.stfranciscatamarans.com/our-history"],
        120,
        "estimated",
        "Official site states more than 120 boats built.",
        None,
    ),
    (
        "Knysna Yacht Company",
        [],
        ["manufacturer", "yard"],
        "South Africa",
        "Rest of World",
        "active",
        2002,
        None,
        "exact",
        "https://www.knysnayachtco.com/",
        None,
        ["https://www.knysnayachtco.com/about-knysna-yacht-company/"],
        100,
        "estimated",
        "Current company material states more than 100 builds.",
        None,
    ),
    (
        "VOYAGE Yachts",
        [],
        ["manufacturer", "yard"],
        "South Africa",
        "Rest of World",
        "active",
        1994,
        None,
        "exact",
        "https://www.voyageyachts.com/",
        None,
        ["https://www.voyageyachts.com/about-us"],
        150,
        "estimated",
        "Industry material reports well over 150 catamarans historically.",
        None,
    ),
    (
        "Cavalier Yachts",
        [],
        ["manufacturer", "yard"],
        "New Zealand",
        "Asia-Pacific",
        "historical",
        1970,
        1979,
        "estimated",
        None,
        None,
        ["https://www.petersmith.net.nz/about/peter.php", "https://cav36.com/"],
        None,
        "unknown",
        "Multiple repeated production series verified; no normalized lifetime total.",
        None,
    ),
]

RECORD_FIELDS = {
    "preferred_display_name",
    "aliases",
    "entity_kind",
    "country",
    "region",
    "status",
    "production_era",
    "relationships",
    "series_production_evidence",
    "official_current_site",
    "official_heritage_archive",
    "other_archive_sources",
    "sources",
    "rights_assessment",
    "model_yield_estimate",
    "ambiguity_notes",
}


def normalize_raw(raw: dict, rid: str) -> dict:
    old_status = raw.pop("review_status")
    rec = {k: v for k, v in raw.items() if k in RECORD_FIELDS}
    name = rec["preferred_display_name"]

    rec["research_record_id"] = rid
    rec["research_status"] = "verified" if name in REVIEWED_VERIFIED else old_status
    if name == "Columbia Yachts":
        rec["research_status"] = "needs_review"
    rec["source_yield_sample"] = False

    if name in BRAND_CONTEXT_ONLY:
        rec["entity_kind"] = ["brand"]
    if name in KIND_PATCH:
        rec["entity_kind"] = KIND_PATCH[name]
    if name in STATUS_PATCH:
        rec["status"] = STATUS_PATCH[name]
    if name in ERA_PATCH:
        start, end, basis = ERA_PATCH[name]
        rec["production_era"] = {"start_year": start, "end_year": end, "basis": basis}
    if name in NOTES:
        rec["ambiguity_notes"] = NOTES[name]
    if name in MODEL_YIELD_PATCH:
        rec["model_yield_estimate"] = MODEL_YIELD_PATCH[name]
    if name in ALIAS_PATCH:
        rec["aliases"] = ALIAS_PATCH[name]
    if name in CLEAR_OFFICIAL_SITE:
        rec["official_current_site"] = None

    # Normalize one checkpoint-only relationship token and mislabeled Wikipedia
    # source types without changing the underlying factual text.
    for rel in rec.get("relationships", []):
        if rel.get("type") == "renamed":
            rel["type"] = "other"
    for src in rec.get("sources", []):
        if "wikipedia.org/" in src.get("url", "") and src.get("source_type") == "wikidata":
            src["source_type"] = "specialist_secondary"

    rec.setdefault("aliases", [])
    rec.setdefault("relationships", [])
    rec.setdefault("other_archive_sources", [])
    rec.setdefault("sources", [])
    rec.setdefault("rights_assessment", [])
    rec.setdefault("official_current_site", None)
    rec.setdefault("official_heritage_archive", None)
    rec.setdefault("ambiguity_notes", None)

    # A small number of recovered records retain a source URL with no
    # corresponding rights/access assessment. Backfill the same conservative
    # default already used for independently researched sources: this is a
    # structural gap closure, not new factual research, and never upgrades
    # any source to CLEARED.
    assessed_urls = {a["source_url"] for a in rec["rights_assessment"]}
    for src in rec["sources"]:
        url = src["url"]
        if url.startswith("http") and url not in assessed_urls:
            rec["rights_assessment"].append(
                {
                    "source_url": url,
                    "public_access": "public",
                    "robots_or_api_notes": "Rights/access assessment backfilled during the SLICE-0019 "
                    "independent-review amendment; public readability does not by itself authorize "
                    "systematic commercial ingestion.",
                    "license_evidence": None,
                    "discovery_use_acceptable": True,
                    "systematic_use_status": "REQUIRES_REVIEW",
                    "review_date": "2026-08-23",
                }
            )
            assessed_urls.add(url)
    rec.setdefault(
        "model_yield_estimate",
        {"value": None, "basis": "unknown", "notes": "No normalized yield retained."},
    )
    legacy_yield = rec.pop("model_yield_estimate")
    rec["model_identity_yield"], rec["production_unit_count"] = split_yield(name, legacy_yield)
    return rec


def make_new(row: tuple, rid: str, packet: str) -> dict:
    (
        name,
        aliases,
        kinds,
        country,
        region,
        status,
        start,
        end,
        basis,
        site,
        heritage,
        urls,
        yield_value,
        yield_basis,
        yield_notes,
        ambiguity,
    ) = row
    sources = [
        {"url": u, "title": f"Source for {name}", "source_type": "other", "retrieved_at": STAMP}
        for u in urls
    ]
    sources.append(
        {
            "url": packet,
            "title": "Independent SLICE-0019 research batch",
            "source_type": "other",
            "retrieved_at": STAMP,
        }
    )
    rights = [
        {
            "source_url": u,
            "public_access": "public",
            "robots_or_api_notes": "Used for bounded manual research; public readability does not authorize systematic commercial ingestion.",
            "license_evidence": None,
            "discovery_use_acceptable": True,
            "systematic_use_status": "REQUIRES_REVIEW",
            "review_date": "2026-08-23",
        }
        for u in urls
    ]
    if name in NEW_ERA_OVERRIDE:
        start, end, basis = NEW_ERA_OVERRIDE[name]
    if yield_value is None:
        model_identity_yield = {"value": None, "basis": yield_basis, "notes": yield_notes}
        production_unit_count = {"value": None, "basis": yield_basis, "notes": yield_notes}
    else:
        # Every non-null NEW-record yield figure is a cumulative
        # production-unit/hull claim (see RESEARCH-007..009); none describes a
        # discoverable model-identity count.
        model_identity_yield = {
            "value": None,
            "basis": "unknown",
            "notes": "No normalized discoverable model-identity count retained; independent research reports "
            "a cumulative production-unit figure instead (see production_unit_count).",
        }
        production_unit_count = {"value": yield_value, "basis": yield_basis, "notes": yield_notes}
    return {
        "research_record_id": rid,
        "preferred_display_name": name,
        "aliases": aliases,
        "entity_kind": kinds,
        "country": country,
        "region": region,
        "status": status,
        "production_era": {"start_year": start, "end_year": end, "basis": basis},
        "relationships": NEW_RELATIONSHIPS.get(name, []),
        "series_production_evidence": "Independent retained research verifies repeated/series sailing-boat production by this manufacturer/yard; entity-specific facts are in the cited sources and research batch.",
        "official_current_site": site,
        "official_heritage_archive": heritage,
        "other_archive_sources": [packet],
        "sources": sources,
        "rights_assessment": rights,
        "model_identity_yield": model_identity_yield,
        "production_unit_count": production_unit_count,
        "research_status": "verified",
        "ambiguity_notes": ambiguity,
        "source_yield_sample": False,
    }


def build() -> dict:
    recovered = []
    for fn in RAW_FILES:
        data = json.loads((RAW / fn).read_text(encoding="utf-8"))
        assert isinstance(data, list), fn
        recovered.extend(data)
    assert len(recovered) == 112, len(recovered)

    records = [normalize_raw(dict(r), f"RSRCH-MFR-{i:04d}") for i, r in enumerate(recovered, 1)]
    packet_by_index = (
        ["repo://research/manufacturers/new_research_batches/RESEARCH-007-southern-europe-core.md"]
        * 8
        + ["repo://research/manufacturers/new_research_batches/RESEARCH-008-asia-core-yards.md"] * 8
        + [
            "repo://research/manufacturers/new_research_batches/RESEARCH-009-australia-new-zealand-south-africa.md"
        ]
        * 8
    )
    for row, packet in zip(NEW, packet_by_index, strict=True):
        records.append(make_new(row, f"RSRCH-MFR-{len(records) + 1:04d}", packet))

    assert len(records) == 136
    return {
        "registry_version": "0019-v1",
        "generated_at": STAMP,
        "slice_id": "SLICE-0019",
        "source_note": (
            "Integrated non-canonical registry from five recovered checkpoint JSON batches, "
            "independent REVIEW-001..006 decisions, and independently sourced RESEARCH-007..009. "
            "The removable temporary external reference is not read and is not evidentiary."
        ),
        "records": records,
    }


def validate(registry: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(instance=registry, schema=schema)

    records = registry["records"]
    assert len({r["research_record_id"] for r in records}) == 136

    statuses = Counter(r["research_status"] for r in records)
    assert statuses == Counter({"verified": 129, "excluded": 6, "needs_review": 1}), statuses

    floor = [
        r
        for r in records
        if r["research_status"] == "verified" and {"manufacturer", "yard"} & set(r["entity_kind"])
    ]
    assert len(floor) == 121, len(floor)

    context = {
        r["preferred_display_name"]
        for r in records
        if r["research_status"] == "verified"
        and not ({"manufacturer", "yard"} & set(r["entity_kind"]))
    }
    assert context == BRAND_CONTEXT_ONLY, sorted(context)

    countries = {r["country"] for r in floor if r["country"]}
    regions = {r["region"] for r in floor}
    historical = sum(r["status"] in {"historical", "defunct", "acquired", "renamed"} for r in floor)
    # Strict floor: an internal HullQ research packet (e.g. RESEARCH-007..009,
    # retained only in other_archive_sources for provenance) never counts as an
    # external official/recognized heritage/archive surface. build_report.py
    # imports this exact helper so the enforced floor and the reported count
    # can never diverge.
    archives = recognized_archive_surface_count(floor)

    assert len(countries) >= 20, len(countries)
    assert len(regions) >= 5, len(regions)
    assert historical >= 40, historical
    assert archives >= 25, archives
    assert sum(r["source_yield_sample"] for r in records) == 0

    validate_verified_invariants(records)

    print("registry schema: PASS")
    print(f"records={len(records)} statuses={dict(statuses)}")
    print(f"manufacturer_yard_floor={len(floor)} countries={len(countries)} regions={len(regions)}")
    print(f"historical_like={historical} recognized_archive_surfaces={archives}")


ID_PATTERN = re.compile(r"^RSRCH-MFR-[0-9]{4}$")


def validate_verified_invariants(records: list[dict]) -> None:
    """Deterministic evidence invariants required for every verified record.

    Every research_status == "verified" manufacturer/yard record must retain:
    non-empty series-production evidence; at least one retained source
    supporting eligibility; a source URL and retrieval date on each source;
    a research-only identifier that is never accidentally reused as a
    canonical HullQ ID; and rights/access coverage for every external URL
    that may later be considered for systematic use.
    """
    for r in records:
        if r["research_status"] != "verified":
            continue
        name = r["preferred_display_name"]
        assert ID_PATTERN.fullmatch(r["research_record_id"]), (
            f"{name}: research_record_id {r['research_record_id']!r} is not a valid "
            "research-only identifier (must never be an accidental canonical HullQ ID)"
        )
        assert r["series_production_evidence"].strip(), (
            f"{name}: missing series-production evidence"
        )
        assert r["sources"], f"{name}: verified record retains no source"
        for src in r["sources"]:
            assert src["url"].strip(), f"{name}: source is missing a URL"
            assert src["retrieved_at"].strip(), f"{name}: source is missing a retrieval date"

        external_urls = {src["url"] for src in r["sources"] if src["url"].startswith("http")}
        assessed_urls = {a["source_url"] for a in r["rights_assessment"]}
        missing_rights = sorted(external_urls - assessed_urls)
        assert not missing_rights, (
            f"{name}: external source(s) {missing_rights} have no rights/access assessment "
            "for possible later systematic use"
        )
        for assessment in r["rights_assessment"]:
            assert (
                assessment["public_access"] != "public"
                or assessment["systematic_use_status"] != "CLEARED"
                or (assessment["license_evidence"])
            ), (
                f"{name}: {assessment['source_url']} is marked CLEARED for systematic use without retained "
                "license/terms evidence; mere public readability must never imply systematic-use clearance"
            )


def main() -> None:
    registry = build()
    validate(registry)
    OUT.write_bytes(
        (json.dumps(registry, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    print(f"wrote={OUT}")


if __name__ == "__main__":
    main()
