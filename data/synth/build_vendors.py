"""Generate the vendor pack. Illustrative values, with MOQs scaled to each SKU's demand."""
import random
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).parents[2]


def main():
    params = yaml.safe_load((ROOT / "data/synth/doc_params.yaml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((ROOT / "data/m5/derived/skus.yaml").read_text(encoding="utf-8"))
    rng = random.Random(params["seed"])
    moq_days = params["moq_days_of_demand"]
    rows = []

    def add(s, role, tier, lead, moq_key):
        vendor_id = f"V{len(rows) + 1:02d}"
        rows.append(
            {
                "sku": s["sku"],
                "vendor_id": vendor_id,
                "role": role,
                "tier": tier,
                "lead_time_days": lead,
                "moq": max(params["min_moq"], round(s["mean_daily_last_year"] * moq_days[moq_key])),
                "penalty_pct": rng.choice([0, 2, 3, 4]),
                "contract_id": f"CON-{vendor_id}",
                "approved_contract": True,
                "unit_cost_usd": round(s["latest_price_usd"] * params["unit_cost_share_of_price"], 2),
                "plant_critical": s["category"] in params["plant_critical_categories"],
            }
        )

    for s in manifest["skus"]:
        add(s, "primary", rng.choice([1, 1, 2]), rng.randint(5, 10), "primary")
        if s["sku"] == params["tier3_trap_sku"]:
            add(s, "alternate", 3, 8, "alternate")
        if s["sku"] == params["lead_time_trap_sku"]:
            add(s, "alternate", 2, params["trap_lead_time_days"], "alternate")
        add(s, "alternate", rng.choice([1, 2]), rng.randint(9, 14), "alternate")

    pd.DataFrame(rows).to_csv(ROOT / "data/synth/vendors.csv", index=False)
    print("wrote vendors.csv rows", len(rows))


if __name__ == "__main__":
    main()
