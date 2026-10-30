"""Write a small derived M5 extract: 15 SKUs, with real sales rolled up to each location in configs/network.yaml.

Reads raw files from M5_DATA_DIR and never modifies them. Selection is deterministic. Candidates sell steadily
in every region (under 10% zero days in the last year, at least MIN_DAILY_UNITS a day) and were on sale in every
store for the full window. The 15 are then taken in turn from three rankings on chain-wide demand, so the set
mixes weekly pattern, trend and volatility, with no category holding more than MAX_PER_CATEGORY.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).parents[2]
N_SKUS = 15
MAX_ZERO_SHARE = 0.10
MIN_DAILY_UNITS = 5
MAX_PER_CATEGORY = 7
LAST_YEAR_DAYS = 365
KEEP_DAYS = 1095
OUT = Path(__file__).parent / "derived"


def score(series: pd.DataFrame, weekdays: np.ndarray) -> pd.DataFrame:
    """Selection metrics over the last year, one row per item."""
    last_year = series.iloc[:, -LAST_YEAR_DAYS:].to_numpy(dtype=float)
    wd = weekdays[-LAST_YEAR_DAYS:]
    means = last_year.mean(axis=1)
    day_means = np.stack([last_year[:, wd == d].mean(axis=1) for d in np.unique(wd)], axis=1)
    return pd.DataFrame(
        {
            "zero_share": (last_year == 0).mean(axis=1),
            "mean_daily": means,
            "weekly_strength": day_means.std(axis=1) / np.maximum(means, 1e-9),
            "trend": np.abs(last_year[:, -90:].mean(axis=1) / np.maximum(last_year[:, :90].mean(axis=1), 1e-9) - 1),
            "volatility": last_year.std(axis=1) / np.maximum(means, 1e-9),
        },
        index=series.index,
    )


def pick(candidates: pd.DataFrame) -> dict[str, str]:
    rankings = {
        c: candidates.sort_values(c, ascending=False, kind="stable").index.tolist()
        for c in ("weekly_strength", "trend", "volatility")
    }
    categories = candidates["cat_id"]
    chosen: dict[str, str] = {}
    while len(chosen) < N_SKUS:
        for reason, ranking in rankings.items():
            if len(chosen) == N_SKUS:
                break
            used = pd.Series([categories[i] for i in chosen], dtype=object).value_counts()
            item = next(i for i in ranking if i not in chosen and used.get(categories[i], 0) < MAX_PER_CATEGORY)
            chosen[item] = reason
    return dict(sorted(chosen.items()))


def main():
    load_dotenv()
    raw = Path(os.environ["M5_DATA_DIR"])
    network = yaml.safe_load((ROOT / "configs/network.yaml").read_text(encoding="utf-8"))["locations"]
    calendar = pd.read_csv(raw / "calendar.csv", parse_dates=["date"])
    sales = pd.read_csv(raw / "sales_train_evaluation.csv")
    prices = pd.read_csv(raw / "sell_prices.csv")

    day_cols = [c for c in sales.columns if c.startswith("d_")]
    day_info = calendar.set_index("d").loc[day_cols]
    weekdays = day_info["wday"].to_numpy()
    series = {
        loc: sales[sales["store_id"].isin(stores)].groupby("item_id")[day_cols].sum().sort_index()
        for loc, stores in network.items()
    }
    scores = {loc: score(df, weekdays) for loc, df in series.items()}

    recent_weeks = day_info["wm_yr_wk"].iloc[-LAST_YEAR_DAYS:].unique()
    counts = prices[prices["wm_yr_wk"].isin(recent_weeks)].groupby("item_id").size()
    always_on_sale = counts[counts == len(recent_weeks) * len(network["plant"])].index

    regional = [loc for loc in network if loc != "plant"]
    steady = pd.concat(
        [(scores[loc]["zero_share"] < MAX_ZERO_SHARE) & (scores[loc]["mean_daily"] >= MIN_DAILY_UNITS) for loc in regional],
        axis=1,
    ).all(axis=1)
    candidates = scores["plant"][steady & scores["plant"].index.isin(always_on_sale)].join(
        sales.drop_duplicates("item_id").set_index("item_id")[["dept_id", "cat_id"]]
    )
    print("steady candidates:", len(candidates), candidates["cat_id"].value_counts().to_dict())
    chosen = pick(candidates)

    OUT.mkdir(exist_ok=True)
    keep = day_cols[-KEEP_DAYS:]
    frames = []
    for loc, df in series.items():
        long = df.loc[list(chosen), keep].reset_index().melt(id_vars="item_id", var_name="d", value_name="units")
        frames.append(long.assign(location=loc))
    sales_out = pd.concat(frames)
    sales_out["date"] = sales_out["d"].map(day_info["date"]).dt.strftime("%Y-%m-%d")
    sales_out = sales_out.rename(columns={"item_id": "sku"})[["date", "location", "sku", "units"]]
    sales_out.sort_values(["location", "sku", "date"]).to_csv(OUT / "sales.csv", index=False)

    weeks = day_info.loc[keep, "wm_yr_wk"].unique()
    picked_prices = prices[prices["item_id"].isin(chosen) & prices["wm_yr_wk"].isin(weeks)]
    price_frames = [
        picked_prices[picked_prices["store_id"].isin(stores)]
        .groupby(["item_id", "wm_yr_wk"], as_index=False)["sell_price"]
        .mean()
        .round({"sell_price": 2})
        .assign(location=loc)
        for loc, stores in network.items()
    ]
    pd.concat(price_frames).rename(columns={"item_id": "sku"})[["location", "sku", "wm_yr_wk", "sell_price"]].to_csv(
        OUT / "prices.csv", index=False
    )

    latest_week = day_info["wm_yr_wk"].iloc[-1]
    latest = picked_prices[picked_prices["wm_yr_wk"] == latest_week].groupby("item_id")["sell_price"].mean()
    manifest = {
        "stores": network,
        "simulated_today": day_info["date"].iloc[-1].strftime("%Y-%m-%d"),
        "skus": [
            {
                "sku": sku,
                "dept": str(candidates.at[sku, "dept_id"]),
                "category": str(candidates.at[sku, "cat_id"]),
                "selected_for": reason,
                "mean_daily_last_year": {loc: round(float(scores[loc].at[sku, "mean_daily"]), 2) for loc in network},
                "max_zero_share": round(float(max(scores[loc].at[sku, "zero_share"] for loc in network)), 3),
                "latest_price_usd": round(float(latest[sku]), 2),
            }
            for sku, reason in chosen.items()
        ],
    }
    (OUT / "skus.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    for s in manifest["skus"]:
        print(s["sku"], s["selected_for"], s["mean_daily_last_year"], s["max_zero_share"], s["latest_price_usd"])
    print("rows", len(sales_out), "simulated_today", manifest["simulated_today"])


if __name__ == "__main__":
    main()
