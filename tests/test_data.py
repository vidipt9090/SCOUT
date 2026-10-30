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
    assert all(s["max_zero_share"] < 0.10 for s in m["skus"])
    sales = pd.read_csv(DERIVED / "sales.csv")
    assert set(sales["sku"]) == {s["sku"] for s in m["skus"]}
    assert sales["date"].max() == m["simulated_today"]


def test_plant_demand_is_the_sum_of_the_regions():
    sales = pd.read_csv(DERIVED / "sales.csv")
    totals = sales.pivot_table(index=["date", "sku"], columns="location", values="units")
    regions = totals["retail_dc"] + totals["peer_dc_1"] + totals["peer_dc_2"]
    assert (totals["plant"] == regions).all()


def test_eight_shared_vendors_with_a_real_choice_per_sku():
    v = pd.read_csv(ROOT / "data/synth/vendors.csv")
    assert v["vendor_id"].nunique() == 8
    assert (v.groupby("vendor_id")["tier"].nunique() == 1).all()
    assert (v.groupby("vendor_id")["sku"].nunique() > 1).sum() >= 7
    assert not v.duplicated(["sku", "vendor_id"]).any()
    assert (v[v["role"] == "primary"].groupby("sku").size() == 1).all()
    assert (v[v["tier"] < 3].groupby("sku").size() >= 2).all()


def test_inventory_matches_persona_cover():
    inv = pd.read_csv(ROOT / "data/synth/inventory.csv")
    sales = pd.read_csv(DERIVED / "sales.csv")
    start = sorted(sales["date"].unique())[-90]
    daily = sales[sales["date"] >= start].groupby(["location", "sku"])["units"].mean()
    cover = inv.assign(days=inv["on_hand"] / [daily[k] for k in zip(inv["location"], inv["sku"])])
    tolerance = 0.5  # on_hand is rounded to whole units
    plant = cover[cover["location"] == "plant"]
    assert (plant["days"] > plant["safety_floor_days"]).all()
    assert plant["days"].between(2, 3 + tolerance).all()
    retail = cover[cover["location"] == "retail_dc"]
    assert retail["days"].between(21 - tolerance, 28 + tolerance).all()
    peers = cover[cover["location"].str.startswith("peer_dc")]
    assert (peers["days"] > 10).all()
