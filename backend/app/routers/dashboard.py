from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.data_processing import records_to_dataframe
from app.services.forecasting import forecast_all_departments
from app.services.anomaly_detection import summarize_high_risk_departments

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

_EMPTY_DASHBOARD = dict(
    total_budget=0, total_income=0, total_expenditure=0, total_surplus=0,
    remaining_budget=0, budget_utilization_pct=0, anomalies_detected=0,
    active_departments=0, total_transactions=0, department_wise_spending=[],
    quarterly_trends=[], top_expense_heads=[],
    grant_utilization={"grant_expenditure": 0, "total_expenditure": 0, "utilization_pct": 0},
    forecast_summary={"next_period_total_predicted": 0, "departments_forecasted": 0},
    anomaly_summary={"total_flagged": 0, "top_risk_department": None},
)


@router.get("/years")
def list_dashboard_years(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns one summary card per financial year the current user has data
    for — e.g. [{"financial_year": "2025-2026", "report_count": 1,
    "total_budget": ..., "total_expenditure": ..., "transaction_count": ...}].
    Meant to drive a "click a year to open that year's dashboard" UI:
    the frontend renders one card per entry, and clicking it calls
    GET /api/dashboard/summary?financial_year=<that year>.
    """
    df = records_to_dataframe(db, user_id=current_user.id)
    if df.empty:
        return {"years": []}

    if current_user.role.value == "hod" and current_user.department:
        df = df[df["department"] == current_user.department]

    report_years_by_fy = (
        db.query(models.Report.report_year)
        .filter(models.Report.user_id == current_user.id)
        .all()
    )
    report_count_by_fy: dict = {}
    for (fy,) in report_years_by_fy:
        if fy:
            report_count_by_fy[fy] = report_count_by_fy.get(fy, 0) + 1

    grouped = df.groupby("financial_year").agg(
        total_budget=("budget_allocated", "sum"),
        total_expenditure=("actual_expenditure", "sum"),
        transaction_count=("number_of_transactions", "sum"),
        anomalies_detected=("anomalies_detected", "sum"),
    ).reset_index().round(2)

    years = []
    for _, row in grouped.sort_values("financial_year", ascending=False).iterrows():
        fy = row["financial_year"]
        years.append({
            "financial_year": fy,
            "report_count": report_count_by_fy.get(fy, 0),
            "total_budget": float(row["total_budget"]),
            "total_expenditure": float(row["total_expenditure"]),
            "transaction_count": int(row["transaction_count"]),
            "anomalies_detected": int(row["anomalies_detected"]),
        })

    return {"years": years}


@router.get("/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(
    financial_year: Optional[str] = Query(
        None, description="Restrict the dashboard to one financial year, e.g. '2025-2026'. "
                           "Omit to see the aggregate across all of the user's reports/years."
    ),
    report_id: Optional[int] = Query(None, description="Restrict the dashboard to a single owned report."),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    df = records_to_dataframe(db, user_id=current_user.id, report_id=report_id)

    if df.empty:
        return schemas.DashboardSummary(**_EMPTY_DASHBOARD)

    if financial_year:
        df = df[df["financial_year"] == financial_year]
        if df.empty:
            return schemas.DashboardSummary(**_EMPTY_DASHBOARD)

    # HOD role sees only their own department's data
    if current_user.role.value == "hod" and current_user.department:
        df = df[df["department"] == current_user.department]
        if df.empty:
            return schemas.DashboardSummary(**_EMPTY_DASHBOARD)

    total_budget = float(df["budget_allocated"].sum())
    total_expenditure = float(df["actual_expenditure"].sum())
    remaining_budget = float(df["remaining_budget"].sum())
    utilization = (total_expenditure / total_budget * 100) if total_budget else 0.0

    # "Total Income" is represented by budget_allocated (sanctioned funds)
    # in the structured transaction schema — see sql_query_engine.py for
    # the same convention used by the RAG assistant's numeric answers.
    total_income = total_budget
    total_surplus = total_income - total_expenditure

    dept_spending = df.groupby("department").agg(
        budget=("budget_allocated", "sum"),
        expenditure=("actual_expenditure", "sum"),
    ).reset_index().round(2)
    dept_spending_list = dept_spending.to_dict(orient="records")

    q_trend = df.groupby(["financial_year", "quarter"]).agg(
        expenditure=("actual_expenditure", "sum"),
        budget=("budget_allocated", "sum"),
    ).reset_index()
    q_trend["period"] = q_trend["financial_year"] + " " + q_trend["quarter"]
    q_trend_list = q_trend[["period", "expenditure", "budget"]].round(2).to_dict(orient="records")

    top_heads = (
        df.groupby("major_expense_head")["actual_expenditure"].sum()
        .sort_values(ascending=False).head(6).reset_index()
        .rename(columns={"major_expense_head": "expense_head", "actual_expenditure": "amount"})
        .round(2).to_dict(orient="records")
    )

    # Grant Utilization: expenditure booked against any expense head whose
    # name mentions "grant" (e.g. "Research Grants"), as a share of total
    # expenditure. This is a proxy pending a dedicated grants ledger.
    grant_mask = df["major_expense_head"].fillna("").str.contains("grant", case=False)
    grant_expenditure = float(df.loc[grant_mask, "actual_expenditure"].sum())
    grant_utilization = {
        "grant_expenditure": round(grant_expenditure, 2),
        "total_expenditure": round(total_expenditure, 2),
        "utilization_pct": round((grant_expenditure / total_expenditure * 100) if total_expenditure else 0.0, 2),
    }

    # Forecast Summary: quick institution-wide next-period figure so the
    # dashboard doesn't require a separate call to /api/forecast just to
    # show a headline number.
    try:
        forecasts = forecast_all_departments(df, engine="linear")
        forecast_summary = {
            "next_period_total_predicted": round(sum(f["predicted_expenditure"] for f in forecasts), 2),
            "departments_forecasted": len(forecasts),
        }
    except Exception:
        forecast_summary = {"next_period_total_predicted": 0, "departments_forecasted": 0}

    # Anomaly Summary: pull the latest persisted anomaly rows for this user
    # (and this year, if scoped) rather than re-running Isolation Forest on
    # every dashboard load.
    txn_ids = set(df["id"].tolist())
    anomaly_query = db.query(models.Anomaly).filter(
        models.Anomaly.user_id == current_user.id, models.Anomaly.is_anomaly == True  # noqa: E712
    )
    anomaly_rows = [a for a in anomaly_query.all() if a.transaction_id in txn_ids]
    anomaly_summary = {"total_flagged": len(anomaly_rows), "top_risk_department": None}
    if anomaly_rows:
        dept_counts: dict = {}
        for a in anomaly_rows:
            dept_counts[a.department] = dept_counts.get(a.department, 0) + 1
        anomaly_summary["top_risk_department"] = max(dept_counts, key=dept_counts.get)

    return schemas.DashboardSummary(
        total_budget=round(total_budget, 2),
        total_income=round(total_income, 2),
        total_expenditure=round(total_expenditure, 2),
        total_surplus=round(total_surplus, 2),
        remaining_budget=round(remaining_budget, 2),
        budget_utilization_pct=round(utilization, 2),
        anomalies_detected=int(df["anomalies_detected"].sum()),
        active_departments=int(df["department"].nunique()),
        total_transactions=int(df["number_of_transactions"].sum()),
        department_wise_spending=dept_spending_list,
        quarterly_trends=q_trend_list,
        top_expense_heads=top_heads,
        grant_utilization=grant_utilization,
        forecast_summary=forecast_summary,
        anomaly_summary=anomaly_summary,
    )
