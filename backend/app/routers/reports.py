import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.services.data_processing import records_to_dataframe
from app.services.report_generator import generate_pdf_report, generate_excel_report

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.post("/generate")
def generate_report(
    payload: schemas.ReportRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    df = records_to_dataframe(db, user_id=current_user.id)

    if payload.export_format == "excel":
        content = generate_excel_report(
            df, payload.report_type, payload.financial_year, payload.quarter, payload.department
        )
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{payload.report_type}_report.xlsx"
    else:
        content = generate_pdf_report(
            df, payload.report_type, payload.financial_year, payload.quarter, payload.department
        )
        media_type = "application/pdf"
        filename = f"{payload.report_type}_report.pdf"

    db.add(models.AuditLog(
        user_email=current_user.email, action="REPORT_GENERATED",
        details=f"{payload.report_type} report ({payload.export_format})"
    ))
    db.commit()

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
