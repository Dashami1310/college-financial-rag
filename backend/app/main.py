"""
RAG Based Financial Expenditure Analytics and Anomaly Detection System
for Technical Institution
=================================================================================
FastAPI application entry point.

Run locally:
    cd backend
    pip install -r requirements.txt
    alembic upgrade head        # applies the Postgres schema migrations
    python seed_data.py         # seeds demo users + sample report
    uvicorn app.main:app --reload --port 8000

Docs available at: http://localhost:8000/docs
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import (
    auth, dashboard, upload, analytics, anomaly, forecast, rag,
    reports, report_management,
)

app = FastAPI(
    title="RAG Based Financial Expenditure Analytics and Anomaly Detection System for Technical Institution",
    description=(
        "Multi-user audit analytics platform — CSV/Excel and PDF audit-report "
        "ingestion, ML-based anomaly detection, time-series forecasting, and a "
        "RAG + Gemini powered financial question-answering assistant, with "
        "per-user report ownership and JWT authentication."
    ),
    version="2.0.0",
)

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/", tags=["Health"])
def root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "docs": "/docs",
    }


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(upload.router)
app.include_router(analytics.router)
app.include_router(anomaly.router)
app.include_router(forecast.router)
app.include_router(rag.router)
app.include_router(reports.router)             # report generation/export (PDF/Excel)
app.include_router(report_management.router)   # report CRUD / ownership (list/get/delete)


if FRONTEND_DIST.is_dir():
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        requested_file = (FRONTEND_DIST / full_path).resolve()
        try:
            requested_file.relative_to(FRONTEND_DIST.resolve())
        except ValueError:
            raise HTTPException(status_code=404, detail="Not Found")
        if requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(FRONTEND_DIST / "index.html")
