"""Fit a simple baseline per SKU offline and cache a 30-day forecast. Never fits inside a timed run.

Each SKU uses whichever of seasonal naive and a fixed SARIMA has the lower MAE on the last 28 days.
Model orders are fixed, not searched.
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

ROOT = Path(__file__).parents[2]
HOLDOUT = 28
HORIZON = 30
TRAIN_DAYS = 365


def seasonal_naive(train: np.ndarray, steps: int) -> np.ndarray:
    week = train[-7:]
    return np.resize(week, steps)


def sarima(train: np.ndarray, steps: int) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = SARIMAX(train, order=(1, 0, 1), seasonal_order=(0, 1, 1, 7)).fit(disp=False)
    return np.clip(fit.forecast(steps), 0, None)


MODELS = {"seasonal_naive": seasonal_naive, "sarima_101_011_7": sarima}


def main():
    sales = pd.read_csv(ROOT / "data/m5/derived/sales.csv")
    out = {}
    for sku, group in sales.groupby("sku"):
        y = group.sort_values("date")["units"].to_numpy(dtype=float)[-TRAIN_DAYS:]
        train, test = y[:-HOLDOUT], y[-HOLDOUT:]
        errors = {}
        for name, model in MODELS.items():
            try:
                errors[name] = float(np.abs(model(train, HOLDOUT) - test).mean())
            except (ValueError, np.linalg.LinAlgError) as e:
                print("skip", sku, name, e)
        best = min(errors, key=errors.get)
        out[sku] = {
            "model": best,
            "holdout_mae": {k: round(v, 3) for k, v in errors.items()},
            "daily_forecast": [round(float(v), 3) for v in MODELS[best](y, HORIZON)],
        }
        print(sku, best, out[sku]["holdout_mae"])
    (ROOT / "data/forecasting/baselines.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
