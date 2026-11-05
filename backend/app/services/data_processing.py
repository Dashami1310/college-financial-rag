from __future__ import annotations

import io
from typing import Tuple, List, Dict

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app import models

REQUIRED_COLUMNS = [
    "financial_year",
    "quarter",
    "department",
    "budget_allocated",
    "actual_expenditure",
]

OPTIONAL_COLUMNS = [
    "remaining_budget",
    "major_expense_head",
    "number_of_transactions",
    "vendor",
    "approval_status",
    "anomalies_detected",
    "forecast_next_quarter",
]

VALID_DEPARTMENTS = {
    "AIML", "CSE", "ISE", "ECE", "EEE", "Mechanical", "Civil",
    "Biotechnology", "Chemical", "Textile", "MBA", "MCA",
    "Library", "Administration", "Training & Placement",
    # Synthetic whole-institution bucket used for category-level
    # income/expenditure ledgers that have no department dimension
    # (see transform_income_expenditure_ledger below).
    "Institution",
}

# Maps common header variants -> canonical snake_case column name
COLUMN_ALIASES = {
    "financial year": "financial_year",
    "fy": "financial_year",
    "quarter": "quarter",
    "qtr": "quarter",
    "department": "department",
    "dept": "department",
    "budget allocated": "budget_allocated",
    "allocated budget": "budget_allocated",
    "actual expenditure": "actual_expenditure",
    "expenditure": "actual_expenditure",
    "remaining budget": "remaining_budget",
    "major expense head": "major_expense_head",
    "expense head": "major_expense_head",
    "number of transactions": "number_of_transactions",
    "transactions": "number_of_transactions",
    "vendor": "vendor",
    "approval status": "approval_status",
    "status": "approval_status",
    "anomalies detected": "anomalies_detected",
    "forecast next quarter": "forecast_next_quarter",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    new_cols = {}
    for col in df.columns:
        key = str(col).strip().lower()
        canonical = COLUMN_ALIASES.get(key, key.replace(" ", "_"))
        new_cols[col] = canonical
    return df.rename(columns=new_cols)


def read_dataset(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Reads a CSV or Excel file into a normalized DataFrame."""
    if filename.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        df = pd.read_csv(io.BytesIO(file_bytes))
    df = _normalize_columns(df)
    return df


def validate_dataset(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validates presence of required columns and basic data sanity."""
    warnings: List[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return False, [f"Missing required column(s): {', '.join(missing)}"]

    if df.empty:
        return False, ["Uploaded dataset contains no rows."]

    unknown_depts = set(df["department"].dropna().astype(str).str.strip()) - VALID_DEPARTMENTS
    if unknown_depts:
        warnings.append(
            f"Unrecognized department name(s) found (will still be imported): {', '.join(sorted(unknown_depts))}"
        )

    numeric_cols = ["budget_allocated", "actual_expenditure"]
    for col in numeric_cols:
        non_numeric = pd.to_numeric(df[col], errors="coerce").isna() & df[col].notna()
        if non_numeric.any():
            warnings.append(f"Non-numeric values found in '{col}' — rows will be coerced/dropped.")

    return True, warnings


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans, fills defaults, and computes derived columns."""
    df = df.copy()

    # Ensure all optional columns exist
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Strip whitespace on text columns
    text_cols = ["financial_year", "quarter", "department", "major_expense_head",
                 "vendor", "approval_status"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Numeric coercion
    df["budget_allocated"] = pd.to_numeric(df["budget_allocated"], errors="coerce").fillna(0.0)
    df["actual_expenditure"] = pd.to_numeric(df["actual_expenditure"], errors="coerce").fillna(0.0)
    df["number_of_transactions"] = pd.to_numeric(
        df["number_of_transactions"], errors="coerce"
    ).fillna(0).astype(int)

    # Remaining budget: recompute if missing/invalid
    computed_remaining = df["budget_allocated"] - df["actual_expenditure"]
    remaining_col = pd.to_numeric(df["remaining_budget"], errors="coerce")
    df["remaining_budget"] = remaining_col.where(remaining_col.notna(), computed_remaining)

    # Approval status default
    df["approval_status"] = df["approval_status"].replace("nan", np.nan).fillna("Approved")

    # Anomalies detected -> boolean
    df["anomalies_detected"] = df["anomalies_detected"].apply(
        lambda v: str(v).strip().lower() in ("1", "true", "yes", "y") if pd.notna(v) else False
    )

    # Forecast next quarter numeric (optional, may be overwritten by forecasting module)
    df["forecast_next_quarter"] = pd.to_numeric(df["forecast_next_quarter"], errors="coerce")

    # Drop fully empty rows
    df = df.dropna(subset=["department", "financial_year", "quarter"], how="any")
    df = df[df["department"].str.lower() != "nan"]

    return df.reset_index(drop=True)


def dataframe_summary(df: pd.DataFrame) -> Dict:
    """Generates a quick statistical summary used for the upload preview screen."""
    return {
        "row_count": int(len(df)),
        "departments": sorted(df["department"].unique().tolist()),
        "financial_years": sorted(df["financial_year"].unique().tolist()),
        "quarters": sorted(df["quarter"].unique().tolist()),
        "total_budget_allocated": float(df["budget_allocated"].sum()),
        "total_actual_expenditure": float(df["actual_expenditure"].sum()),
        "avg_expenditure_per_record": float(df["actual_expenditure"].mean()) if len(df) else 0.0,
        "missing_values": int(df.isna().sum().sum()),
    }


def persist_transactions(db: Session, df: pd.DataFrame, report: "models.Report", user_id: int) -> int:
    """Bulk-inserts cleaned rows into `transactions`, linked to a report and its owner."""
    records = []
    for _, row in df.iterrows():
        records.append(
            models.Transaction(
                report_id=report.id,
                user_id=user_id,
                financial_year=str(row["financial_year"]),
                quarter=str(row["quarter"]),
                department=str(row["department"]),
                budget_allocated=float(row["budget_allocated"]),
                actual_expenditure=float(row["actual_expenditure"]),
                remaining_budget=float(row["remaining_budget"]),
                major_expense_head=(None if pd.isna(row.get("major_expense_head"))
                                     else str(row.get("major_expense_head"))),
                number_of_transactions=int(row["number_of_transactions"]),
                vendor=(None if pd.isna(row.get("vendor")) else str(row.get("vendor"))),
                approval_status=str(row["approval_status"]),
                anomalies_detected=bool(row["anomalies_detected"]),
                forecast_next_quarter=(None if pd.isna(row.get("forecast_next_quarter"))
                                        else float(row.get("forecast_next_quarter"))),
            )
        )
    db.bulk_save_objects(records)
    db.commit()
    return len(records)


def records_to_dataframe(db: Session, user_id: int = None, report_id: int = None) -> pd.DataFrame:
    """
    Loads transactions back into a DataFrame for analytics/ML, always scoped
    to the requesting user (report ownership enforcement) and optionally to
    a single report.
    """
    query = db.query(models.Transaction)
    if user_id is not None:
        query = query.filter(models.Transaction.user_id == user_id)
    if report_id is not None:
        query = query.filter(models.Transaction.report_id == report_id)
    rows = query.all()
    data = [{
        "id": r.id,
        "report_id": r.report_id,
        "financial_year": r.financial_year,
        "quarter": r.quarter,
        "department": r.department,
        "budget_allocated": r.budget_allocated,
        "actual_expenditure": r.actual_expenditure,
        "remaining_budget": r.remaining_budget,
        "major_expense_head": r.major_expense_head,
        "number_of_transactions": r.number_of_transactions,
        "vendor": r.vendor,
        "approval_status": r.approval_status,
        "anomalies_detected": r.anomalies_detected,
        "forecast_next_quarter": r.forecast_next_quarter,
    } for r in rows]
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Alternate schema adapter: institution-wide Income & Expenditure ledger
# ---------------------------------------------------------------------------
# Real audited financial statements are frequently exported in a simple
# category-level ledger shape rather than the per-department, per-quarter
# budget-vs-actual shape the rest of this module expects:
#
#     Year, Category, Subcategory, Amount
#     2025, Income,      Fee Collection,           566282724
#     2025, Expenditure, Salary & Establishment,   248159216
#
# There is no department dimension and no separate "allocated budget" figure
# (these are audited actuals, not a budget/variance system) — so rather than
# forcing the uploader to reshape their data, this adapter detects that
# shape and maps it onto the existing `transactions` schema automatically:
#
#     financial_year      = str(Year)                     e.g. "2025"
#     quarter              = "Annual"  (no quarterly data available)
#     department            = "Institution"  (synthetic whole-institution bucket)
#     major_expense_head   = Subcategory
#     budget_allocated     = Amount   (Income rows only, else 0)
#     actual_expenditure   = Amount   (Expenditure rows only, else 0)
#     remaining_budget     = budget_allocated - actual_expenditure
#
# This makes SUM(budget_allocated) == Total Income and
# SUM(actual_expenditure) == Total Expenditure across the whole ledger,
# which is exactly what the dashboard / SQL query engine already expect
# under the "Total Income = sum(budget_allocated)" convention established
# in sql_query_engine.py — so every downstream module (dashboard, anomaly
# detection, forecasting, RAG) works against it unmodified.
INCOME_EXPENDITURE_LEDGER_COLUMNS = {"year", "category", "subcategory", "amount"}


def is_income_expenditure_ledger_format(df: pd.DataFrame) -> bool:
    """Detects the Year/Category/Subcategory/Amount ledger shape."""
    return INCOME_EXPENDITURE_LEDGER_COLUMNS.issubset(set(df.columns))


def transform_income_expenditure_ledger(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts a Year/Category/Subcategory/Amount ledger into the standard
    `transactions` shape (see module docstring above for the exact mapping).
    Returns a DataFrame ready for `dataframe_summary()` / `persist_transactions()`
    — the same functions used by the standard department-quarterly path.
    """
    df = df.copy()
    df["year"] = df["year"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df["subcategory"] = df["subcategory"].astype(str).str.strip()
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    is_income = df["category"].str.lower() == "income"
    is_expenditure = df["category"].str.lower() == "expenditure"

    unknown_categories = set(df.loc[~(is_income | is_expenditure), "category"].unique())

    out = pd.DataFrame({
        "financial_year": df["year"],
        "quarter": "Annual",
        "department": "Institution",
        "major_expense_head": df["subcategory"],
        "budget_allocated": df["amount"].where(is_income, 0.0),
        "actual_expenditure": df["amount"].where(is_expenditure, 0.0),
        "number_of_transactions": 1,
        "vendor": None,
        "approval_status": "Approved",
        "anomalies_detected": False,
        "forecast_next_quarter": None,
    })
    out["remaining_budget"] = out["budget_allocated"] - out["actual_expenditure"]

    if unknown_categories:
        # Rows with a category other than Income/Expenditure are kept (both
        # budget_allocated and actual_expenditure will be 0 for them) rather
        # than silently dropped, but flagged so the upload response can warn
        # the user instead of quietly ignoring data.
        out.attrs["unknown_categories"] = sorted(unknown_categories)

    return out.reset_index(drop=True)
