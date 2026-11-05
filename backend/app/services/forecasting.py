from __future__ import annotations

import warnings
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

QUARTER_ORDER = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3}

# Keep the model search small because forecasting runs once per department.
# These two lightweight candidates retain AIC-based selection without
# fitting several redundant models for every dashboard/page request.
_ARIMA_ORDER_GRID = [(1, 0, 0), (1, 1, 0)]


def _period_sort_key(row) -> tuple:
    try:
        year = int(str(row["financial_year"]).split("-")[0])
    except Exception:
        year = 0
    q = QUARTER_ORDER.get(str(row["quarter"]).upper(), 0)
    return (year, q)


def _next_period_label(last_year: str, last_quarter: str) -> tuple:
    try:
        year_start = int(str(last_year).split("-")[0])
    except Exception:
        year_start = 2026

    q_key = str(last_quarter).upper()
    if q_key not in QUARTER_ORDER:
        # Non-quarterly cadence (e.g. an annual Income & Expenditure ledger
        # where quarter="Annual") — just advance the year and keep the same
        # period label, rather than incorrectly synthesizing a "Q_" label.
        return str(year_start + 1), last_quarter

    q_num = QUARTER_ORDER[q_key]
    if q_num == 3:  # Q4 -> next FY Q1
        return f"{year_start + 1}-{year_start + 2}", "Q1"
    else:
        return last_year, f"Q{q_num + 2}"


def _prepare_series(df: pd.DataFrame, department: str) -> pd.DataFrame:
    dept_df = df[df["department"] == department].copy()
    if dept_df.empty:
        return dept_df
    dept_df["sort_key"] = dept_df.apply(_period_sort_key, axis=1)
    dept_df = dept_df.sort_values("sort_key")
    grouped = dept_df.groupby(["financial_year", "quarter"], sort=False).agg(
        actual_expenditure=("actual_expenditure", "sum"),
        budget_allocated=("budget_allocated", "sum"),
    ).reset_index()
    grouped["sort_key"] = grouped.apply(_period_sort_key, axis=1)
    grouped = grouped.sort_values("sort_key").reset_index(drop=True)
    grouped["period_label"] = grouped["financial_year"] + " " + grouped["quarter"]
    return grouped


def _fallback_forecast(y: np.ndarray) -> tuple:
    """Weighted moving average / linear regression — the original Phase-1
    engine, used for short histories or when ARIMA fails to fit."""
    n = len(y)
    if n == 1:
        predicted = float(y[0])
        residual_std = predicted * 0.1
    elif n < 4:
        weights = np.arange(1, n + 1)
        predicted = float(np.average(y, weights=weights))
        residual_std = float(np.std(y)) if n > 1 else predicted * 0.1
    else:
        X = np.arange(n).reshape(-1, 1)
        model = LinearRegression()
        model.fit(X, y)
        predicted = max(float(model.predict([[n]])[0]), 0.0)
        residuals = y - model.predict(X)
        residual_std = float(np.std(residuals))
    return predicted, residual_std


def _arima_forecast(y: np.ndarray) -> Optional[tuple]:
    """Fits the best-AIC ARIMA order from a small grid and returns a
    1-step-ahead (predicted, lower, upper) tuple, or None if no order in
    the grid could be fit (caller should fall back)."""
    from statsmodels.tsa.arima.model import ARIMA

    best_result = None
    best_aic = np.inf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for order in _ARIMA_ORDER_GRID:
            try:
                model = ARIMA(y, order=order)
                fit = model.fit()
                if fit.aic < best_aic:
                    best_aic = fit.aic
                    best_result = fit
            except Exception:
                continue

    if best_result is None:
        return None

    forecast_obj = best_result.get_forecast(steps=1)
    predicted = float(forecast_obj.predicted_mean[0])
    conf_int = forecast_obj.conf_int(alpha=0.32)  # ~1 std equivalent, matches prior engine's band width
    lower = float(conf_int[0][0]) if hasattr(conf_int, "__getitem__") else float(conf_int.iloc[0, 0])
    upper = float(conf_int[0][1]) if hasattr(conf_int, "__getitem__") else float(conf_int.iloc[0, 1])
    return max(predicted, 0.0), max(lower, 0.0), upper


def _prophet_forecast(history_df: pd.DataFrame) -> Optional[tuple]:
    """
    Prophet engine — implemented and reviewed but NOT executed in the
    sandbox this project was built in (see module docstring / PROPHET_SETUP.md).
    Expects `history_df` with columns ['period_label', 'actual_expenditure'];
    builds a synthetic quarterly date index since Prophet requires an actual
    `ds` datetime column.
    """
    from prophet import Prophet  # noqa: local import — optional heavy dependency

    dates = pd.date_range(
        end=pd.Timestamp.today(), periods=len(history_df), freq="QS"
    )
    prophet_df = pd.DataFrame({
        "ds": dates,
        "y": history_df["actual_expenditure"].values,
    })

    model = Prophet(interval_width=0.68, yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False)
    model.fit(prophet_df)

    future = model.make_future_dataframe(periods=1, freq="QS")
    forecast = model.predict(future)
    last_row = forecast.iloc[-1]

    predicted = max(float(last_row["yhat"]), 0.0)
    lower = max(float(last_row["yhat_lower"]), 0.0)
    upper = float(last_row["yhat_upper"])
    return predicted, lower, upper


def forecast_department(df: pd.DataFrame, department: str, engine: str = "arima") -> Dict:
    """Forecasts next quarter expenditure for a single department using the
    requested engine ("arima" or "prophet"), with automatic fallback to the
    lightweight engine for short histories or fit failures."""
    grouped = _prepare_series(df, department)
    if grouped.empty:
        return {"department": department, "forecast": None, "history": []}

    history = grouped[["period_label", "actual_expenditure", "budget_allocated"]].to_dict(orient="records")
    y = grouped["actual_expenditure"].values.astype(float)
    n = len(y)

    if n == 0:
        return {"department": department, "forecast": None, "history": history}

    used_engine = "linear"
    predicted = lower = upper = None

    if engine == "prophet" and n >= 4:
        try:
            result = _prophet_forecast(grouped)
            if result:
                predicted, lower, upper = result
                used_engine = "prophet"
        except Exception as e:
            print(f"[WARN] Prophet forecast failed for {department}, falling back: {e}")

    if predicted is None and engine in ("arima", "prophet") and n >= 4:
        try:
            result = _arima_forecast(y)
            if result:
                predicted, lower, upper = result
                used_engine = "arima"
        except Exception as e:
            print(f"[WARN] ARIMA forecast failed for {department}, falling back: {e}")

    if predicted is None:
        predicted, residual_std = _fallback_forecast(y)
        lower = max(predicted - residual_std, 0.0)
        upper = predicted + residual_std
        used_engine = "linear" if n >= 4 else "weighted_moving_average"

    last_row = grouped.iloc[-1]
    next_year, next_quarter = _next_period_label(last_row["financial_year"], last_row["quarter"])
    period_label = f"{next_year} {next_quarter}"

    suggested_budget = round((predicted * 1.10) / 1000) * 1000

    return {
        "department": department,
        "history": history,
        "forecast": {
            "period_label": period_label,
            "predicted_expenditure": round(predicted, 2),
            "lower_bound": round(lower, 2),
            "upper_bound": round(upper, 2),
            "suggested_budget": round(suggested_budget, 2),
            "engine": used_engine,
        },
    }


def forecast_all_departments(df: pd.DataFrame, engine: str = "arima") -> List[Dict]:
    results = []
    for dept in sorted(df["department"].dropna().unique()):
        res = forecast_department(df, dept, engine=engine)
        if res["forecast"]:
            results.append({"department": dept, **res["forecast"]})
    return results


def annual_trend(df: pd.DataFrame) -> List[Dict]:
    """Aggregates total expenditure/budget by financial year for trend charting."""
    if df.empty:
        return []
    agg = df.groupby("financial_year").agg(
        total_budget=("budget_allocated", "sum"),
        total_expenditure=("actual_expenditure", "sum"),
    ).reset_index().sort_values("financial_year")
    return agg.to_dict(orient="records")
