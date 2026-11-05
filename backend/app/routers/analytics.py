from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.auth import get_current_user
from app.services.data_processing import records_to_dataframe

router = APIRouter(prefix="/api/analytics", tags=["Financial Analytics"])


def _apply_filters(df, financial_year, quarter, department):
    if financial_year:
        df = df[df["financial_year"] == financial_year]
    if quarter:
        df = df[df["quarter"] == quarter]
    if department:
        df = df[df["department"] == department]
    return df


@router.get("/filters")
def get_filter_options(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    df = records_to_dataframe(db, user_id=current_user.id)
    if df.empty:
        return {"financial_years": [], "quarters": [], "departments": []}
    return {
        "financial_years": sorted(df["financial_year"].dropna().unique().tolist()),
        "quarters": sorted(df["quarter"].dropna().unique().tolist()),
        "departments": sorted(df["department"].dropna().unique().tolist()),
    }


@router.get("/breakdown")
def expenditure_breakdown(
    financial_year: Optional[str] = Query(None),
    quarter: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    df = records_to_dataframe(db, user_id=current_user.id)
    if df.empty:
        return {"records": 0, "by_department": [], "by_expense_head": [], "by_quarter": []}

    df = _apply_filters(df, financial_year, quarter, department)

    by_department = df.groupby("department").agg(
        budget_allocated=("budget_allocated", "sum"),
        actual_expenditure=("actual_expenditure", "sum"),
        remaining_budget=("remaining_budget", "sum"),
        transactions=("number_of_transactions", "sum"),
    ).reset_index().round(2).to_dict(orient="records")

    by_expense_head = df.groupby("major_expense_head").agg(
        actual_expenditure=("actual_expenditure", "sum"),
    ).reset_index().sort_values("actual_expenditure", ascending=False).round(2).to_dict(orient="records")

    by_quarter = df.groupby(["financial_year", "quarter"]).agg(
        budget_allocated=("budget_allocated", "sum"),
        actual_expenditure=("actual_expenditure", "sum"),
    ).reset_index().round(2)
    by_quarter["period"] = by_quarter["financial_year"] + " " + by_quarter["quarter"]

    return {
        "records": int(len(df)),
        "by_department": by_department,
        "by_expense_head": by_expense_head,
        "by_quarter": by_quarter.to_dict(orient="records"),
    }


@router.get("/utilization")
def budget_utilization(
    financial_year: Optional[str] = Query(None),
    quarter: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    df = records_to_dataframe(db, user_id=current_user.id)
    if df.empty:
        return {"data": []}

    df = _apply_filters(df, financial_year, quarter, department)
    grouped = df.groupby("department").agg(
        budget_allocated=("budget_allocated", "sum"),
        actual_expenditure=("actual_expenditure", "sum"),
    ).reset_index()
    grouped["utilization_pct"] = grouped.apply(
        lambda r: round((r["actual_expenditure"] / r["budget_allocated"] * 100), 2)
        if r["budget_allocated"] else 0.0, axis=1
    )
    return {"data": grouped.round(2).to_dict(orient="records")}


@router.get("/compare")
def compare_departments(
    departments: str = Query(..., description="Comma-separated department names, e.g. AIML,CSE"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    dept_list = [d.strip() for d in departments.split(",") if d.strip()]
    df = records_to_dataframe(db, user_id=current_user.id)
    if df.empty:
        return {"data": []}

    filtered = df[df["department"].isin(dept_list)]
    grouped = filtered.groupby("department").agg(
        budget_allocated=("budget_allocated", "sum"),
        actual_expenditure=("actual_expenditure", "sum"),
        remaining_budget=("remaining_budget", "sum"),
        transactions=("number_of_transactions", "sum"),
        anomalies=("anomalies_detected", "sum"),
    ).reset_index().round(2)
    return {"data": grouped.to_dict(orient="records")}
