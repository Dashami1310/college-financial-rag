from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.data_processing import records_to_dataframe
from app.services.forecasting import (
    forecast_department, forecast_all_departments, annual_trend
)

router = APIRouter(prefix="/api/forecast", tags=["Forecasting"])

VALID_ENGINES = {"arima", "prophet"}


@router.get("", response_model=schemas.ForecastResponse)
def get_forecast(
    department: Optional[str] = Query(None),
    report_id: Optional[int] = Query(None),
    engine: Optional[str] = Query(
        None, description="Forecast engine: 'arima' (default, tested) or 'prophet' "
                           "(implemented, see PROPHET_SETUP.md). Falls back automatically "
                           "to a lightweight engine for short histories or fit failures."
    ),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    resolved_engine = engine or settings.FORECAST_ENGINE
    if resolved_engine not in VALID_ENGINES:
        resolved_engine = "arima"

    df = records_to_dataframe(db, user_id=current_user.id, report_id=report_id)
    if df.empty:
        return schemas.ForecastResponse(department=department, history=[], forecast=[], annual_trend=[])

    trend = annual_trend(df)

    if department:
        result = forecast_department(df, department, engine=resolved_engine)
        forecast_list = []
        if result["forecast"]:
            forecast_list = [schemas.ForecastOut(department=department, **result["forecast"])]
        return schemas.ForecastResponse(
            department=department,
            history=result["history"],
            forecast=forecast_list,
            annual_trend=trend,
        )

    all_forecasts = forecast_all_departments(df, engine=resolved_engine)
    forecast_list = [schemas.ForecastOut(**f) for f in all_forecasts]
    return schemas.ForecastResponse(department=None, history=[], forecast=forecast_list, annual_trend=trend)


@router.post("/save")
def save_forecast_results(
    report_id: Optional[int] = Query(None),
    engine: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Persists the latest forecast results into the `forecasts` table."""
    resolved_engine = engine or settings.FORECAST_ENGINE
    if resolved_engine not in VALID_ENGINES:
        resolved_engine = "arima"

    df = records_to_dataframe(db, user_id=current_user.id, report_id=report_id)
    if df.empty:
        return {"saved": 0}

    results = forecast_all_departments(df, engine=resolved_engine)

    query = db.query(models.Forecast).filter(models.Forecast.user_id == current_user.id)
    if report_id:
        query = query.filter(models.Forecast.report_id == report_id)
    query.delete(synchronize_session=False)

    target_report_id = report_id
    if target_report_id is None:
        first_report = (
            db.query(models.Report)
            .filter(models.Report.user_id == current_user.id)
            .order_by(models.Report.upload_date.desc())
            .first()
        )
        target_report_id = first_report.id if first_report else None

    rows = [
        models.Forecast(
            report_id=target_report_id,
            user_id=current_user.id,
            department=r["department"],
            period_label=r["period_label"],
            predicted_expenditure=r["predicted_expenditure"],
            lower_bound=r["lower_bound"],
            upper_bound=r["upper_bound"],
            suggested_budget=r["suggested_budget"],
            engine=r.get("engine", resolved_engine),
        )
        for r in results
        if target_report_id is not None
    ]
    db.bulk_save_objects(rows)
    db.commit()
    return {"saved": len(rows)}
