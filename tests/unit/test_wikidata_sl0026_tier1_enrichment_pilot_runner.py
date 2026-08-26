"""Runner-level tests for
scripts/bootstrap/wikidata_sl0026_tier1_enrichment_pilot_runner.py.

Only the fully offline, network-free ``--select`` mode is exercised here
(``run_select``) — deterministic and reproducible from the real committed
SLICE-0017/0018 manifests, writing its own ``selection.json`` to ``tmp_path``
so the real committed
``research/stage3/sl0026-wikidata-tier1-enrichment/`` package is never
touched by tests. ``--live``/``--persist`` require network/PostgreSQL access
respectively and are exercised manually plus by
``tests/persistence/test_wikidata_sl0026_tier1_enrichment_pilot_integration.py``
(for the persistence mechanism) at implementation time.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from bootstrap.wikidata_sl0026_tier1_enrichment_pilot_runner import run_select  # noqa: E402

from hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot import (  # noqa: E402
    ACCEPTED_CANONICAL_BOAT_MODEL_COUNT,
    ACCEPTED_HISTORICAL_CROSSWALK_COUNT,
    PILOT_SIZE,
)


def test_run_select_writes_valid_selection_document(tmp_path: Path) -> None:
    selection_path = tmp_path / "selection.json"
    document = run_select(selection_path=selection_path)

    assert selection_path.exists()
    on_disk = json.loads(selection_path.read_text(encoding="utf-8"))
    assert on_disk == document

    assert document["pilot_size"] == PILOT_SIZE
    assert len(document["boat_models"]) == PILOT_SIZE
    boundary = document["identity_boundary"]
    assert boundary["canonical_boat_model_count"] == ACCEPTED_CANONICAL_BOAT_MODEL_COUNT
    assert boundary["historical_crosswalk_count"] == ACCEPTED_HISTORICAL_CROSSWALK_COUNT

    qids = [m["qid"] for m in document["boat_models"]]
    ids = [m["hullq_id"] for m in document["boat_models"]]
    assert len(set(qids)) == PILOT_SIZE
    assert len(set(ids)) == PILOT_SIZE
    assert ids == sorted(ids)


def test_run_select_is_deterministic(tmp_path: Path) -> None:
    doc1 = run_select(selection_path=tmp_path / "a" / "selection.json")
    doc2 = run_select(selection_path=tmp_path / "b" / "selection.json")
    assert doc1["boat_models"] == doc2["boat_models"]
    assert doc1["identity_boundary"] == doc2["identity_boundary"]
