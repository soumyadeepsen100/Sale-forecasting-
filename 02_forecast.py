"""Step 2: train & compare forecasting models (time-based split), then
write test predictions and a 6-month future forecast back to SQL."""
import sqlite3, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")
DB = Path(__file__).parent / "sales.db"
TEST_START = "2017-01-01"      # train: 2014-2016, test: 2017 (never a random split)
HORIZON = 6                    # months to forecast beyond the data


def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    return {"MAE": np.mean(np.abs(y - p)),
            "RMSE": np.sqrt(np.mean((y - p) ** 2)),
            "MAPE_%": np.mean(np.abs((y - p) / y)) * 100}


# ---------- feature builder (uses only past values -> no leakage) ----------
def make_row(hist, month):
    """hist: list of past sales. month: pandas Timestamp being predicted."""
    return [hist[-1], hist[-2], hist[-3], hist[-12],
            np.mean(hist[-3:]), month.month, month.quarter]


def build_training(series):
    X, y = [], []
    vals = list(series.values)
    for i in range(12, len(vals)):
        X.append(make_row(vals[:i], series.index[i]))
        y.append(vals[i])
    return np.array(X), np.array(y)


def ml_forecast(model, train, future_index):
    """Recursive multi-step forecast: each prediction feeds the next lag."""
    X, y = build_training(train)
    model.fit(X, y)
    hist, preds = list(train.values), []
    for m in future_index:
        p = float(model.predict([make_row(hist, m)])[0])
        preds.append(p)
        hist.append(p)
    return np.array(preds)


def main():
    con = sqlite3.connect(DB)
    s = pd.read_sql("SELECT month, sales FROM monthly_sales ORDER BY month", con,
                    parse_dates=["month"]).set_index("month")["sales"]
    s.index = pd.DatetimeIndex(s.index, freq="MS")
    train, test = s[s.index < TEST_START], s[s.index >= TEST_START]

    results, preds = {}, {}

    # 1. Baseline: seasonal naive (same month last year)
    preds["Seasonal Naive"] = train.values[-12:][: len(test)]
    # 2. SARIMA
    sar = SARIMAX(train, order=(1, 1, 1), seasonal_order=(1, 1, 0, 12)).fit(disp=False)
    preds["SARIMA"] = sar.forecast(len(test)).values
    # 3-4. ML with lag features
    preds["Random Forest"] = ml_forecast(
        RandomForestRegressor(n_estimators=300, random_state=42, min_samples_leaf=2),
        train, test.index)
    preds["Gradient Boosting"] = ml_forecast(
        GradientBoostingRegressor(n_estimators=150, max_depth=2, learning_rate=0.05,
                                  random_state=42), train, test.index)

    for name, p in preds.items():
        results[name] = metrics(test.values, p)
    res = pd.DataFrame(results).T.round(2).sort_values("RMSE")
    print("\nTest-set results (2017, multi-step, lower is better):\n", res, "\n")

    # Baseline is a yardstick, not a deployable model: pick the best real model
    best = res.drop(index="Seasonal Naive").index[0]
    print("Best model by RMSE (excluding baseline):", best)

    # ---------- refit best on ALL data, forecast the future ----------
    future_idx = pd.date_range(s.index[-1] + pd.offsets.MonthBegin(1), periods=HORIZON, freq="MS")
    if best == "SARIMA":
        full = SARIMAX(s, order=(1, 1, 1), seasonal_order=(1, 1, 0, 12)).fit(disp=False)
        fut = full.forecast(HORIZON).values
    elif best == "Seasonal Naive":
        fut = s.values[-12:][:HORIZON]
    elif best == "Random Forest":
        fut = ml_forecast(RandomForestRegressor(n_estimators=300, random_state=42,
                                                min_samples_leaf=2), s, future_idx)
    else:
        fut = ml_forecast(GradientBoostingRegressor(n_estimators=150, max_depth=2,
                          learning_rate=0.05, random_state=42), s, future_idx)

    # ---------- write everything back to SQL ----------
    con.execute("DROP TABLE IF EXISTS model_metrics")
    con.execute("DROP TABLE IF EXISTS predictions")
    res.reset_index(names="model").to_sql("model_metrics", con, index=False)
    rows = []
    for name, p in preds.items():
        rows += [(name, m.strftime("%Y-%m-01"), "test", float(a), float(v))
                 for m, a, v in zip(test.index, test.values, p)]
    rows += [(best, m.strftime("%Y-%m-01"), "future", None, float(v))
             for m, v in zip(future_idx, fut)]
    pd.DataFrame(rows, columns=["model", "month", "kind", "actual", "predicted"]) \
        .to_sql("predictions", con, index=False)
    con.commit()
    print(f"\n{HORIZON}-month forecast ({best}):")
    for m, v in zip(future_idx, fut):
        print(f"  {m:%b %Y}: {v:,.0f}")
    con.close()


if __name__ == "__main__":
    main()
