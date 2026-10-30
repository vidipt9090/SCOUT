"""Write a small derived M5 extract: one store, 15 SKUs. Reads raw files from M5_DATA_DIR and never modifies them.

Selection is deterministic. Candidates sell steadily (under 10% zero days in the last year) and were on sale
for the full window. The 15 are then taken in turn from three rankings so the set mixes weekly pattern, trend
and volatility, with no category holding more than MAX_PER_CATEGORY.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv

N_SKUS = 15
MAX_ZERO_SHARE = 0.10
MAX_PER_CATEGORY = 7
LAST_YEAR_DAYS = 365
KEEP_DAYS = 1095
OUT = Path(__file__).parent / "derived"


def score_candidates(sales: pd.DataFrame, day_cols: list[str], weekdays: np.ndarray) -> pd.DataFrame:
    last_year = sales[day_cols[-LAST_YEAR_DAYS:]].to_numpy(dtype=float)
    wd = weekdays[-LAST_YEAR_DAYS:]
    means = last_year.mean(axis=1)
    day_means = np.stack([last_year[:, wd == d].mean(axis=1) for d in np.unique(wd)], axis=1)
    return sales[["item_id", "dept_id", "cat_id", "store_id"]].assign(
        zero_share=(last_year == 0).mean(axis=1),
        mean_daily=means,
        weekly_strength=day_means.std(axis=1) / np.maximum(means, 1e-9),
        trend=np.abs(last_year[:, -90:].mean(axis=1) / np.maximum(last_year[:, :90].mean(axis=1), 1e-9) - 1),
        volatility=last_year.std(axis=1) / np.maximum(means, 1e-9),
    )


def pick(candidates: pd.DataFrame) -> pd.DataFrame:
    rankings = {
        c: candidates.sort_values([c, "item_id"], ascending=[False, True])["item_id"].tolist()
        for c in ("weekly_strength", "trend", "volatility")
    }
    categories = candidates.set_index("item_id")["cat_id"]
    chosen: dict[str, str] = {}
    while len(chosen) < N_SKUS:
        for reason, ranking in rankings.items():
            if len(chosen) == N_SKUS:
                break
            used = pd.Series([categories[i] for i in chosen]).value_counts()
            item = next(
                i for i in ranking if i not in chosen and used.get(categories[i], 0) < MAX_PER_CATEGORY
            )
            chosen[item] = reason
    picked = candidates[candidates["item_id"].isin(chosen)].copy()
    picked["selected_for"] = picked["item_id"].map(chosen)
    return picked.sort_values("item_id")


def main():
    load_dotenv()
    raw = Path(os.environ["M5_DATA_DIR"])
    calendar = pd.read_csv(raw / "calendar.csv", parse_dates=["date"])
    sales = pd.read_csv(raw / "sales_train_evaluation.csv")
    prices = pd.read_csv(raw / "sell_prices.csv")

    day_cols = [c for c in sales.columns if c.startswith("d_")]
    day_info = calendar.set_index("d").loc[day_cols]
    scores = score_candidates(sales, day_cols, day_info["wday"].to_numpy())

    recent_weeks = day_info["wm_yr_wk"].iloc[-LAST_YEAR_DAYS:].unique()
    priced = prices[prices["wm_yr_wk"].isin(recent_weeks)].groupby(["store_id", "item_id"]).size()
    full_price = priced[priced == len(recent_weeks)].index
    scores = scores[pd.MultiIndex.from_frame(scores[["store_id", "item_id"]]).isin(full_price)]

    candidates = scores[scores["zero_share"] < MAX_ZERO_SHARE]
    counts = candidates["store_id"].value_counts().sort_index()
    print("steady candidates per store:", counts.to_dict())
    store = counts.sort_values(ascending=False, kind="stable").index[0]
    picked = pick(candidates[candidates["store_id"] == store])

    OUT.mkdir(exist_ok=True)
    keep = day_cols[-KEEP_DAYS:]
    long = (
        sales[(sales["store_id"] == store) & sales["item_id"].isin(picked["item_id"])]
        .melt(id_vars="item_id", value_vars=keep, var_name="d", value_name="units")
        .assign(date=lambda df: df["d"].map(day_info["date"]).dt.strftime("%Y-%m-%d"))
        .rename(columns={"item_id": "sku"})[["date", "sku", "units"]]
        .sort_values(["sku", "date"])
    )
    long.to_csv(OUT / "sales.csv", index=False)

    weeks = day_info.loc[keep, "wm_yr_wk"].unique()
    (
        prices[(prices["store_id"] == store) & prices["item_id"].isin(picked["item_id"]) & prices["wm_yr_wk"].isin(weeks)]
        .rename(columns={"item_id": "sku"})[["sku", "wm_yr_wk", "sell_price"]]
        .sort_values(["sku", "wm_yr_wk"])
        .to_csv(OUT / "prices.csv", index=False)
    )

    latest_week = day_info["wm_yr_wk"].iloc[-1]
    latest = prices[(prices["store_id"] == store) & (prices["wm_yr_wk"] == latest_week)].set_index("item_id")["sell_price"]
    manifest = {
        "store": store,
        "simulated_today": day_info["date"].iloc[-1].strftime("%Y-%m-%d"),
        "skus": [
            {
                "sku": r.item_id,
                "dept": r.dept_id,
                "category": r.cat_id,
                "selected_for": r.selected_for,
                "mean_daily_last_year": round(float(r.mean_daily), 2),
                "zero_share": round(float(r.zero_share), 3),
                "latest_price_usd": float(latest[r.item_id]),
            }
            for r in picked.itertuples()
        ],
    }
    (OUT / "skus.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    print(picked[["item_id", "cat_id", "selected_for", "mean_daily", "zero_share"]].to_string(index=False))
    print("store", store, "rows", len(long), "simulated_today", manifest["simulated_today"])


if __name__ == "__main__":
    main()
