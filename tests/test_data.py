from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
yaml = pytest.importorskip("yaml")

ROOT = Path(__file__).parent.parent
DERIVED = ROOT / "data/m5/derived"
pytestmark = pytest.mark.skipif(not (DERIVED / "sales.csv").exists(), reason="run make m5-extract first")


def manifest():
    return yaml.safe_load((DERIVED / "skus.yaml").read_text(encoding="utf-8"))


def test_fifteen_steady_skus_from_one_store():
    m = manifest()
    assert len({s["sku"] for s in m["skus"]}) == 15
    assert all(s["zero_share"] < 0.10 for s in m["skus"])
    sales = pd.read_csv(DERIVED / "sales.csv")
    assert set(sales["sku"]) == {s["sku"] for s in m["skus"]}
    assert sales["date"].max() == m["simulated_today"]


def test_inventory_matches_persona_cover():
    inv = pd.read_csv(ROOT / "data/synth/inventory.csv")
    sales = pd.read_csv(DERIVED / "sales.csv")
    start = sorted(sales["date"].unique())[-90]
    daily = sales[sales["date"] >= start].groupby("sku")["units"].mean()
    cover = inv.assign(days=inv["on_hand"] / inv["sku"].map(daily))
    tolerance = 0.5  # on_hand is rounded to whole units
    plant = cover[cover["location"] == "plant"]
    assert (plant["days"] > plant["safety_floor_days"]).all()
    assert plant["days"].between(2, 3 + tolerance).all()
    retail = cover[cover["location"] == "retail_dc"]
    assert retail["days"].between(21 - tolerance, 28 + tolerance).all()
    peers = cover[cover["location"].str.startswith("peer_dc")]
    assert (peers["days"] > 10).all()
