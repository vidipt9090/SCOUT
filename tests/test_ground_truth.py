"""The written procedure must yield exactly the ground-truth action in every cell."""
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).parent.parent
TO_ACTION = {"reorder_expedited": "reorder"}


def load(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_procedure_matches_ground_truth_in_every_cell():
    truth = load("data/scenarios/ground_truth.yaml")
    procedure = load("data/synth/doc_params.yaml")["procedure"]
    checked = 0
    for dtype, levels in truth["cells"].items():
        for level, personas in levels.items():
            severity = truth["severity_levels"][level]
            for persona, cell in personas.items():
                written = procedure[persona][severity][dtype]
                assert TO_ACTION.get(written, written) == cell["action"], (dtype, level, persona)
                checked += 1
    assert checked == 18


def test_no_labels_in_agent_visible_config():
    for path in ("configs/personas/plant.yaml", "configs/personas/retail_dc.yaml", "configs/policy.yaml"):
        text = (ROOT / path).read_text(encoding="utf-8").lower()
        assert "expected_action" not in text and "ground_truth" not in text
