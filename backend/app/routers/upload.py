import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.config import settings, UPLOAD_DIR, REPORTS_DIR
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user, require_roles
from app.services import data_processing, pdf_processing
from app.services.rag_pipeline import build_vectorstore_for_user

router = APIRouter(prefix="/api/upload", tags=["Dataset / Report Upload"])

ALLOWED_EXTENSIONS = {".csv": "csv", ".xlsx": "excel", ".xls": "excel"}


@router.post("", response_model=schemas.UploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin", "accounts_staff")),
):
    """
    Uploads a CSV/Excel expenditure sheet, creates an owned `Report` row
    (report_type=csv/excel), persists cleaned rows as `Transaction`s scoped
    to that report + the uploading user, and rebuilds that user's private
    RAG vector index so no data ever crosses between users' financial data.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .csv, .xlsx, .xls files are supported.")

    file_bytes = await file.read()

    try:
        raw_df = data_processing.read_dataset(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    warnings: list[str] = []

    # Auto-detect an alternate schema: an institution-wide Income &
    # Expenditure ledger (Year, Category, Subcategory, Amount) — e.g. a
    # real audited financial statement export — rather than the standard
    # per-department, per-quarter budget-vs-actual shape. If detected, it's
    # transformed onto the standard `transactions` schema automatically so
    # every downstream module (dashboard, anomaly detection, forecasting,
    # RAG) works against it unmodified. See data_processing.py for the
    # exact field mapping and rationale.
    if data_processing.is_income_expenditure_ledger_format(raw_df):
        clean_df = data_processing.transform_income_expenditure_ledger(raw_df)
        unknown_categories = clean_df.attrs.get("unknown_categories")
        if unknown_categories:
            warnings.append(
                f"Row(s) with unrecognized Category value(s) {unknown_categories} were kept "
                f"but not counted as either income or expenditure (expected 'Income' or 'Expenditure')."
            )
        warnings.append(
            "Detected an institution-wide Income & Expenditure ledger (Year/Category/Subcategory/"
            "Amount format, no department or quarter breakdown). Rows were mapped to a synthetic "
            "'Institution' department and 'Annual' quarter — see the project README for details."
        )
    else:
        is_valid, messages = data_processing.validate_dataset(raw_df)
        if not is_valid:
            raise HTTPException(status_code=422, detail={"errors": messages})
        clean_df = data_processing.clean_dataset(raw_df)
        warnings.extend(messages)

    summary = data_processing.dataframe_summary(clean_df)

    # Save the uploaded file to disk
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = UPLOAD_DIR / stored_name
    dest_path.write_bytes(file_bytes)

    report_years = summary["financial_years"]
    report_year_label = report_years[0] if len(report_years) == 1 else (
        f"{report_years[0]} to {report_years[-1]}" if report_years else None
    )

    report = models.Report(
        user_id=current_user.id,
        report_name=Path(file.filename).stem,
        report_year=report_year_label,
        report_type=ALLOWED_EXTENSIONS[ext],
        status=models.ReportStatus.READY,
        file_path=str(dest_path),
        original_filename=file.filename,
        row_count=len(clean_df),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    data_processing.persist_transactions(db, clean_df, report, current_user.id)

    db.add(models.AuditLog(
        user_email=current_user.email, action="REPORT_UPLOAD",
        details=f"Uploaded {file.filename} ({len(clean_df)} rows) as report #{report.id}"
    ))
    db.commit()

    # Rebuild the RAG vector index (transactions + any existing audit chunks)
    # scoped to this user only — tenant isolation, one user's chat assistant
    # must never surface another user's financial data.
    try:
        build_vectorstore_for_user(db, user_id=current_user.id)
    except Exception as e:
        # Non-fatal: upload still succeeds even if RAG indexing has an issue
        print(f"[WARN] Vector store build failed for user {current_user.id}: {e}")

    preview = clean_df.head(10).fillna("").to_dict(orient="records")

    return schemas.UploadResponse(
        report=schemas.ReportOut.model_validate(report),
        preview=preview,
        summary=summary,
        warnings=warnings,
    )


@router.post("/pdf")
async def upload_audit_pdf(
    file: UploadFile = File(...),
    report_name: str = Form(None),
    report_year: str = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_roles("admin", "accounts_staff")),
):
    """
    Phase 2 workflow: Upload PDF Audit Report -> Text Extraction ->
    Section Detection -> Section-Aware Chunking -> persisted as `AuditChunk`
    rows -> RAG vector index rebuilt (combined with the user's existing
    transactions) so the assistant can immediately answer questions about
    the newly uploaded audit report.

    Financial figures embedded in the PDF's prose are NOT yet extracted
    into structured `Transaction` rows (that lands in Phase 3's SQL+RAG
    hybrid query classifier) — this endpoint covers ingestion, section
    detection, chunking, and retrieval only.
    """
    ext = Path(file.filename).suffix.lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Only .pdf files are supported on this endpoint.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Save the raw PDF to disk immediately so it isn't lost even if
    # processing fails partway through.
    stored_name = f"{uuid.uuid4().hex}.pdf"
    dest_path = REPORTS_DIR / stored_name
    dest_path.write_bytes(file_bytes)

    report = models.Report(
        user_id=current_user.id,
        report_name=report_name or Path(file.filename).stem,
        report_year=report_year,  # may be overwritten below by auto-detection
        report_type=models.ReportType.PDF,
        status=models.ReportStatus.PROCESSING,
        file_path=str(dest_path),
        original_filename=file.filename,
        row_count=0,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    try:
        result = pdf_processing.process_audit_pdf(
            file_bytes,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
    except Exception as e:
        report.status = models.ReportStatus.FAILED
        db.commit()
        raise HTTPException(status_code=422, detail=f"Failed to process PDF: {e}")

    if not report.report_year and result["detected_year"]:
        report.report_year = result["detected_year"]

    chunk_rows = [
        models.AuditChunk(
            report_id=report.id,
            year=report.report_year,
            section=c["section"],
            chunk_index=c["chunk_index"],
            chunk_text=c["chunk_text"],
        )
        for c in result["chunks"]
    ]
    db.bulk_save_objects(chunk_rows)

    report.status = models.ReportStatus.READY
    report.row_count = len(chunk_rows)
    db.commit()
    db.refresh(report)

    db.add(models.AuditLog(
        user_email=current_user.email, action="AUDIT_PDF_UPLOAD",
        details=(
            f"Uploaded {file.filename} as report #{report.id} "
            f"({len(chunk_rows)} chunks across {len(result['sections_found'])} sections)"
        )
    ))
    db.commit()

    try:
        build_vectorstore_for_user(db, user_id=current_user.id)
    except Exception as e:
        print(f"[WARN] Vector store build failed for user {current_user.id}: {e}")

    return {
        "report": schemas.ReportOut.model_validate(report),
        "page_count": result["page_count"],
        "detected_year": result["detected_year"],
        "sections_found": result["sections_found"],
        "section_chunk_counts": result["section_chunk_counts"],
        "total_chunks": len(chunk_rows),
    }


@router.get("/datasets", response_model=list[schemas.ReportOut])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Legacy path, now backed by the `reports` table — still returns only
    the current user's own uploads (ownership enforced)."""
    return (
        db.query(models.Report)
        .filter(models.Report.user_id == current_user.id)
        .order_by(models.Report.upload_date.desc())
        .all()
    )
