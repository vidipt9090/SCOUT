"""Generate the vendor pack: 8 vendors shared across the SKUs, one supply agreement per vendor and SKU.

Tier and penalty belong to the vendor. Lead time, MOQ and unit cost belong to the agreement. Values are illustrative.
"""
import random
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).parents[2]
PRIMARY_POOL_SIZE = 7  # the Tier 3 vendor is never a primary
ALTERNATE_OFFSET = 3


def main():
    params = yaml.safe_load((ROOT / "data/synth/doc_params.yaml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((ROOT / "data/m5/derived/skus.yaml").read_text(encoding="utf-8"))
    rng = random.Random(params["seed"])
    roster = params["vendors"]
    ids = sorted(roster)
    tier3 = next(v for v in ids if roster[v]["tier"] == 3)
    pool = [v for v in ids if v != tier3]
    assert len(pool) == PRIMARY_POOL_SIZE
    moq_days = params["moq_days_of_demand"]
    rows = []

    def add(s, vendor_id, role, lead, moq_key):
        rows.append(
            {
                "sku": s["sku"],
                "vendor_id": vendor_id,
                "role": role,
                "tier": roster[vendor_id]["tier"],
                "lead_time_days": lead,
                "moq": max(params["min_moq"], round(s["mean_daily_last_year"]["retail_dc"] * moq_days[moq_key])),
                "penalty_pct": roster[vendor_id]["penalty_pct"],
                "contract_id": f"CON-{vendor_id}-{s['sku']}",
                "approved_contract": True,
                "unit_cost_usd": round(s["latest_price_usd"] * params["unit_cost_share_of_price"], 2),
                "plant_critical": s["category"] in params["plant_critical_categories"],
            }
        )

    for i, s in enumerate(manifest["skus"]):
        primary = pool[i % PRIMARY_POOL_SIZE]
        alternate = pool[(i + ALTERNATE_OFFSET) % PRIMARY_POOL_SIZE]
        add(s, primary, "primary", rng.randint(5, 10), "primary")
        if s["sku"] == params["tier3_trap_sku"]:
            add(s, tier3, "alternate", 8, "alternate")
        if s["sku"] == params["lead_time_trap_sku"]:
            slow = pool[(i + ALTERNATE_OFFSET + 1) % PRIMARY_POOL_SIZE]
            add(s, slow, "alternate", params["trap_lead_time_days"], "alternate")
        add(s, alternate, "alternate", rng.randint(9, 14), "alternate")

    pd.DataFrame(rows).to_csv(ROOT / "data/synth/vendors.csv", index=False)
    print("wrote vendors.csv agreements", len(rows), "vendors", len({r["vendor_id"] for r in rows}))


if __name__ == "__main__":
    main()
