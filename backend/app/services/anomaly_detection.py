from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.config import settings

FEATURE_COLS = ["utilization_pct", "overspend_amount", "spend_per_transaction", "dept_zscore"]

FEATURE_LABELS = {
    "utilization_pct": "Budget Utilization %",
    "overspend_amount": "Overspend Amount (₹)",
    "spend_per_transaction": "Spend per Transaction (₹)",
    "dept_zscore": "Deviation from Department Peers",
}


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["utilization_pct"] = np.where(
        df["budget_allocated"] > 0,
        df["actual_expenditure"] / df["budget_allocated"] * 100,
        0,
    )
    df["overspend_amount"] = df["actual_expenditure"] - df["budget_allocated"]
    df["spend_per_transaction"] = np.where(
        df["number_of_transactions"] > 0,
        df["actual_expenditure"] / df["number_of_transactions"],
        df["actual_expenditure"],
    )
    # Peer z-score within department
    dept_mean = df.groupby("department")["actual_expenditure"].transform("mean")
    dept_std = df.groupby("department")["actual_expenditure"].transform("std").replace(0, 1).fillna(1)
    df["dept_zscore"] = (df["actual_expenditure"] - dept_mean) / dept_std

    return df


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Runs Isolation Forest over engineered features and returns the input
    DataFrame augmented with: anomaly_score, risk_score (0-100), is_anomaly, reason.
    """
    if df.empty or len(df) < 5:
        df = df.copy()
        df["anomaly_score"] = 0.0
        df["risk_score"] = 0.0
        df["is_anomaly"] = False
        df["reason"] = "Insufficient data for ML-based detection"
        return df

    feat_df = _engineer_features(df)
    feature_cols = FEATURE_COLS
    X = feat_df[feature_cols].replace([np.inf, -np.inf], 0).fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=settings.ISOLATION_FOREST_CONTAMINATION,
        random_state=42,
    )
    model.fit(X_scaled)

    raw_scores = model.decision_function(X_scaled)      # higher = more normal
    predictions = model.predict(X_scaled)                # -1 = anomaly, 1 = normal

    # Normalize risk score to 0-100 (lower decision_function -> higher risk)
    min_s, max_s = raw_scores.min(), raw_scores.max()
    span = (max_s - min_s) or 1.0
    risk_scores = 100 * (1 - (raw_scores - min_s) / span)

    feat_df["anomaly_score"] = raw_scores
    feat_df["risk_score"] = risk_scores.round(2)
    feat_df["is_anomaly"] = predictions == -1

    def _reason(row) -> str:
        reasons = []
        if row["remaining_budget"] < 0 and row["budget_allocated"] > 0:
            reasons.append("Budget violation (overspent)")
        if row["utilization_pct"] > 120:
            reasons.append(f"Overspending: {row['utilization_pct']:.0f}% of allocated budget used")
        if abs(row["dept_zscore"]) > 2:
            reasons.append("Unusual expenditure vs department peers")
        if row["spend_per_transaction"] > feat_df["spend_per_transaction"].mean() * 3:
            reasons.append("Abnormally high spend-per-transaction")
        return "; ".join(reasons) if reasons else "Statistical outlier detected by Isolation Forest"

    feat_df["reason"] = feat_df.apply(lambda r: _reason(r) if r["is_anomaly"] else None, axis=1)

    # SHAP explainability: compute per-feature contribution only for the
    # flagged rows (cheap — typically a small fraction of the dataset),
    # so "why was this transaction flagged?" has a concrete, ranked answer.
    feat_df["shap_explanation"] = None
    anomaly_mask = feat_df["is_anomaly"]
    if anomaly_mask.any():
        try:
            explanations = explain_anomalies(model, X_scaled, feat_df, anomaly_mask)
            anomaly_positions = np.where(anomaly_mask.values)[0]
            shap_col_idx = feat_df.columns.get_loc("shap_explanation")
            for pos, explanation in zip(anomaly_positions, explanations):
                feat_df.iat[pos, shap_col_idx] = explanation
        except Exception as e:
            print(f"[WARN] SHAP explanation failed, continuing without it: {e}")

    return feat_df


def explain_anomalies(model, X_scaled: np.ndarray, feat_df: pd.DataFrame, anomaly_mask: pd.Series) -> List[list]:
    """
    Returns a list (one entry per flagged row, in mask order) of ranked
    per-feature SHAP contributions:
        [{"feature": "Budget Utilization %", "value": 142.3, "contribution": 0.31}, ...]
    Positive contribution = pushed the row toward being flagged as anomalous.
    """
    import shap

    explainer = shap.TreeExplainer(model)
    anomaly_indices = np.where(anomaly_mask.values)[0]
    shap_values = explainer.shap_values(X_scaled[anomaly_indices])

    results = []
    for row_i, original_idx in enumerate(anomaly_indices):
        row = feat_df.iloc[original_idx]
        contributions = shap_values[row_i]
        ranked = sorted(
            zip(FEATURE_COLS, contributions),
            key=lambda t: abs(t[1]),
            reverse=True,
        )
        results.append([
            {
                "feature": FEATURE_LABELS[feat],
                "value": round(float(row[feat]), 2),
                "contribution": round(float(contrib), 4),
            }
            for feat, contrib in ranked
        ])
    return results


def summarize_high_risk_departments(anomaly_df: pd.DataFrame) -> List[Dict]:
    if anomaly_df.empty:
        return []
    agg = (
        anomaly_df.groupby("department")
        .agg(
            avg_risk_score=("risk_score", "mean"),
            anomalies_count=("is_anomaly", "sum"),
            total_expenditure=("actual_expenditure", "sum"),
        )
        .reset_index()
        .sort_values("avg_risk_score", ascending=False)
    )
    agg["avg_risk_score"] = agg["avg_risk_score"].round(2)
    return agg.to_dict(orient="records")
