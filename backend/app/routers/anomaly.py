from typing import Optional
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.data_processing import records_to_dataframe
from app.services.anomaly_detection import detect_anomalies, summarize_high_risk_departments

router = APIRouter(prefix="/api/anomaly", tags=["Anomaly Detection"])


@router.get("/detect", response_model=schemas.AnomalyDetectionResponse)
def run_anomaly_detection(
    financial_year: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    report_id: Optional[int] = Query(None, description="Restrict detection to a single owned report"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    df = records_to_dataframe(db, user_id=current_user.id, report_id=report_id)
    if df.empty:
        return schemas.AnomalyDetectionResponse(
            total_records_analyzed=0, anomalies_found=0,
            high_risk_departments=[], results=[]
        )

    if financial_year:
        df = df[df["financial_year"] == financial_year]
    if department:
        df = df[df["department"] == department]

    result_df = detect_anomalies(df)

    # Persist latest anomaly results (replace old ones for these transactions)
    transaction_ids = result_df["id"].tolist()
    if transaction_ids:
        db.query(models.Anomaly).filter(
            models.Anomaly.transaction_id.in_(transaction_ids)
        ).delete(synchronize_session=False)

        rows_to_add = []
        for _, row in result_df.iterrows():
            shap_json = json.dumps(row["shap_explanation"]) if row.get("shap_explanation") else None
            rows_to_add.append(models.Anomaly(
                report_id=int(row["report_id"]),
                user_id=current_user.id,
                transaction_id=int(row["id"]),
                department=row["department"],
                financial_year=row["financial_year"],
                quarter=row["quarter"],
                anomaly_score=float(row["anomaly_score"]),
                risk_score=float(row["risk_score"]),
                is_anomaly=bool(row["is_anomaly"]),
                reason=row["reason"],
                shap_explanation=shap_json,
            ))
        db.bulk_save_objects(rows_to_add)

        # Sync the anomalies_detected flag back onto transactions
        anomaly_ids = result_df[result_df["is_anomaly"]]["id"].tolist()
        if anomaly_ids:
            db.query(models.Transaction).filter(
                models.Transaction.id.in_(anomaly_ids)
            ).update({models.Transaction.anomalies_detected: True}, synchronize_session=False)
        db.commit()

    high_risk = summarize_high_risk_departments(result_df)

    results = [
        schemas.AnomalyOut(
            id=idx,
            transaction_id=int(row["id"]),
            department=row["department"],
            financial_year=row["financial_year"],
            quarter=row["quarter"],
            anomaly_score=round(float(row["anomaly_score"]), 4),
            risk_score=float(row["risk_score"]),
            is_anomaly=bool(row["is_anomaly"]),
            reason=row["reason"],
            shap_explanation=row.get("shap_explanation"),
        )
        for idx, (_, row) in enumerate(
            result_df.sort_values("risk_score", ascending=False).iterrows(), start=1
        )
    ]

    return schemas.AnomalyDetectionResponse(
        total_records_analyzed=int(len(result_df)),
        anomalies_found=int(result_df["is_anomaly"].sum()),
        high_risk_departments=high_risk,
        results=results,
    )


@router.get("/{transaction_id}/explain")
def explain_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Dedicated 'why was this transaction flagged?' endpoint — returns the
    persisted SHAP explanation for a specific transaction's most recent
    anomaly detection run, scoped to the current user.
    """
    anomaly = (
        db.query(models.Anomaly)
        .filter(
            models.Anomaly.transaction_id == transaction_id,
            models.Anomaly.user_id == current_user.id,
        )
        .order_by(models.Anomaly.detected_at.desc())
        .first()
    )
    if not anomaly:
        return {"transaction_id": transaction_id, "explanation": None, "message": "No anomaly record found for this transaction."}

    return {
        "transaction_id": transaction_id,
        "department": anomaly.department,
        "risk_score": anomaly.risk_score,
        "is_anomaly": anomaly.is_anomaly,
        "reason": anomaly.reason,
        "shap_explanation": json.loads(anomaly.shap_explanation) if anomaly.shap_explanation else None,
    }
