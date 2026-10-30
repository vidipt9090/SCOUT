from collections import Counter

import pytest

pytest.importorskip("yaml")
pytest.importorskip("crewai")

from eval.pilot import expand, key  # noqa: E402


def test_grid_sizes_and_unique_keys():
    conditions = expand()
    sizes = Counter(c["block"] for c in conditions)
    assert sizes == {"manipulation": 4, "core": 32, "messaging": 8, "prompt_variance": 4}
    assert len({key(c) for c in conditions}) == 48


def test_expansion_is_reproducible():
    assert expand() == expand()


def test_manipulation_block_runs_first():
    assert {c["block"] for c in expand()[:4]} == {"manipulation"}
