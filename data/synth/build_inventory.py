"""Generate synthetic stock. M5 has no stock levels, so on_hand = 90-day average demand x days of cover."""
import random
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).parents[2]
SEED = 3101
RECENT_DAYS = 90
PEER_DCS = ("peer_dc_1", "peer_dc_2")
PEER_COVER_DAYS = (35, 45)  # assumption: enough slack to pass POL-06 after a transfer
SAFETY_FLOOR_DAYS = {"retail_dc": 7, "peer_dc_1": 10, "peer_dc_2": 10}  # assumption, except plant from persona


def main():
    plant = yaml.safe_load((ROOT / "configs/personas/plant.yaml").read_text(encoding="utf-8"))
    retail = yaml.safe_load((ROOT / "configs/personas/retail_dc.yaml").read_text(encoding="utf-8"))
    sales = pd.read_csv(ROOT / "data/m5/derived/sales.csv")
    recent_start = sorted(sales["date"].unique())[-RECENT_DAYS]
    demand = sales[sales["date"] >= recent_start].groupby("sku")["units"].mean()

    rng = random.Random(SEED)
    rows = []
    for sku, daily in demand.items():
        cover = {
            "plant": plant["days_of_cover_start"],
            "retail_dc": rng.uniform(*retail["days_of_cover_start"]),
            **{dc: rng.uniform(*PEER_COVER_DAYS) for dc in PEER_DCS},
        }
        floors = {"plant": plant["hard_constraint"]["safety_floor_days"], **SAFETY_FLOOR_DAYS}
        for location, days in cover.items():
            rows.append(
                {
                    "location": location,
                    "sku": sku,
                    "on_hand": round(daily * days),
                    "safety_floor_days": floors[location],
                }
            )
    out = ROOT / "data/synth/inventory.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print("wrote", out.name, "rows", len(rows))


if __name__ == "__main__":
    main()
