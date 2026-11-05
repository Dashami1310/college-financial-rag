"""
Report Management Router
==========================
Implements the multi-report ownership workflow:
    - list all reports belonging to the current user
    - view a single owned report's metadata
    - delete an owned report (cascades to its transactions/anomalies/
      forecasts/audit_chunks via SQLAlchemy relationship cascade)
    - "select" a report as active for dashboard/analytics scoping (the
      frontend passes report_id as a query param to the other routers;
      this endpoint makes the set of selectable reports listable)

Ownership is enforced on every endpoint: a user can only see/act on rows
where `Report.user_id == current_user.id`. Admins do not get a silent
bypass here — per the specification, ownership is strict.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/api/reports", tags=["Report Management"])


def _get_owned_report(db: Session, report_id: int, user: models.User) -> models.Report:
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if report.user_id != user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this report.")
    return report


@router.get("/mine", response_model=list[schemas.ReportOut])
def list_my_reports(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Report)
        .filter(models.Report.user_id == current_user.id)
        .order_by(models.Report.upload_date.desc())
        .all()
    )


@router.get("/{report_id}", response_model=schemas.ReportOut)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_owned_report(db, report_id, current_user)


@router.get("/{report_id}/sections")
def get_report_sections(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Returns the section-aware breakdown of a PDF audit report — how many
    chunks were detected per section (Income & Expenditure, Balance Sheet,
    Grant Assets, Depreciation, Audit Observations, Notes to Accounts, or
    General for anything before the first recognized heading).
    """
    report = _get_owned_report(db, report_id, current_user)
    chunks = db.query(models.AuditChunk).filter(models.AuditChunk.report_id == report.id).all()

    section_counts: dict = {}
    for c in chunks:
        section_counts[c.section or "General"] = section_counts.get(c.section or "General", 0) + 1

    return {
        "report_id": report.id,
        "report_name": report.report_name,
        "report_type": report.report_type,
        "total_chunks": len(chunks),
        "sections": section_counts,
    }


@router.get("/{report_id}/chunks")
def get_report_chunks(
    report_id: int,
    section: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Returns the raw text chunks for a report, optionally filtered to one section."""
    report = _get_owned_report(db, report_id, current_user)
    query = db.query(models.AuditChunk).filter(models.AuditChunk.report_id == report.id)
    if section:
        query = query.filter(models.AuditChunk.section == section)
    chunks = query.order_by(models.AuditChunk.section, models.AuditChunk.chunk_index).all()

    return [
        {
            "id": c.id,
            "section": c.section,
            "year": c.year,
            "chunk_index": c.chunk_index,
            "chunk_text": c.chunk_text,
        }
        for c in chunks
    ]


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    report = _get_owned_report(db, report_id, current_user)

    if report.file_path:
        try:
            from pathlib import Path
            file_path = Path(report.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"[WARN] Could not remove file for report {report_id}: {e}")

    db.add(models.AuditLog(
        user_email=current_user.email, action="REPORT_DELETED",
        details=f"Deleted report #{report.id} ({report.report_name})"
    ))
    db.delete(report)  # cascades to transactions/anomalies/forecasts/audit_chunks
    db.commit()

    # Rebuild the user's RAG index so deleted data is no longer retrievable
    try:
        from app.services.rag_pipeline import build_vectorstore_for_user
        build_vectorstore_for_user(db, user_id=current_user.id)
    except Exception as e:
        print(f"[WARN] Vector store rebuild after delete failed: {e}")

    return {"status": "deleted", "report_id": report_id}
