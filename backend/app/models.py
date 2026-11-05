"""
Database schema (SQLAlchemy ORM models) — Phase 1 upgrade.

"RAG Based Financial Expenditure Analytics and Anomaly Detection System
for Technical Institution"

This replaces the earlier file-oriented "datasets" model with a proper
multi-user, multi-report architecture as required for the audit-analytics
upgrade, while preserving every existing capability (RBAC roles, CSV/Excel
ingestion, anomaly detection, forecasting, RAG chat, report export).

Tables
------
users          -> authentication + RBAC (admin, accounts_staff, hod, principal)
revoked_tokens -> JWT logout support (blacklist of revoked token IDs)
reports        -> one row per uploaded report (CSV/Excel *or* PDF audit report),
                  always owned by exactly one user
transactions   -> line-level financial records belonging to a report
                  (successor to the old `expenditure_records` table — same
                  fields, now report/user scoped)
anomalies      -> ML (Isolation Forest) anomaly results per transaction,
                  with a slot for SHAP explanation JSON (Phase 5)
forecasts      -> time-series forecast output per department/report
                  (ARIMA/Prophet — Phase 5)
audit_chunks   -> section-aware text chunks extracted from PDF audit reports,
                  the retrieval unit for the RAG pipeline (Phase 2)
chat_history   -> RAG assistant conversation log, optionally scoped to a report
audit_logs     -> tracks uploads / report generation / logins / deletions
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ACCOUNTS_STAFF = "accounts_staff"
    HOD = "hod"
    PRINCIPAL = "principal"


class ReportType(str, enum.Enum):
    CSV = "csv"          # structured expenditure spreadsheet (legacy/simple workflow)
    EXCEL = "excel"
    PDF = "pdf"           # audit report (Phase 2 pipeline)


class ReportStatus(str, enum.Enum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ApprovalStatus(str, enum.Enum):
    APPROVED = "Approved"
    PENDING = "Pending"
    REJECTED = "Rejected"


# ---------------------------------------------------------------------------
# Users & Auth
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Extensions beyond the minimum spec, preserving existing RBAC behavior
    role = Column(Enum(UserRole), default=UserRole.ACCOUNTS_STAFF, nullable=False)
    department = Column(String(80), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    reports = relationship("Report", back_populates="owner", cascade="all, delete-orphan")


class RevokedToken(Base):
    """Enables real JWT logout: a token's unique id (jti) is recorded here and
    rejected on every subsequent request, even though the JWT itself is
    stateless and would otherwise remain valid until it naturally expires."""
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(64), unique=True, index=True, nullable=False)
    user_email = Column(String(120), nullable=True)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Reports (owned by a single user)
# ---------------------------------------------------------------------------
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    report_name = Column(String(255), nullable=False)
    report_year = Column(String(20), nullable=True, index=True)   # e.g. "2025-2026"
    report_type = Column(Enum(ReportType), default=ReportType.CSV, nullable=False)
    status = Column(Enum(ReportStatus), default=ReportStatus.READY, nullable=False)

    file_path = Column(String(500), nullable=True)     # stored PDF/CSV path on disk
    original_filename = Column(String(255), nullable=True)
    row_count = Column(Integer, default=0)

    upload_date = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="reports")
    transactions = relationship("Transaction", back_populates="report", cascade="all, delete-orphan")
    audit_chunks = relationship("AuditChunk", back_populates="report", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="report", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="report", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Transactions (successor to expenditure_records — report/user scoped)
# ---------------------------------------------------------------------------
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    financial_year = Column(String(20), index=True, nullable=False)
    quarter = Column(String(10), index=True, nullable=False)
    department = Column(String(80), index=True, nullable=False)
    budget_allocated = Column(Float, default=0.0)
    actual_expenditure = Column(Float, default=0.0)
    remaining_budget = Column(Float, default=0.0)
    major_expense_head = Column(String(120), nullable=True)
    number_of_transactions = Column(Integer, default=0)
    vendor = Column(String(120), nullable=True)
    approval_status = Column(String(20), default="Approved")
    anomalies_detected = Column(Boolean, default=False)
    forecast_next_quarter = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="transactions")
# ---------------------------------------------------------------------------
# Anomalies
# ---------------------------------------------------------------------------
class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)

    department = Column(String(80))
    financial_year = Column(String(20))
    quarter = Column(String(10))
    anomaly_score = Column(Float)          # raw isolation forest decision_function score
    risk_score = Column(Float)             # normalized 0-100
    is_anomaly = Column(Boolean, default=False)
    reason = Column(String(255), nullable=True)

    # Phase 5: SHAP explainability — JSON-encoded list of
    # {feature, contribution, value} so the frontend can render "why flagged"
    shap_explanation = Column(Text, nullable=True)

    detected_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="anomalies")


# ---------------------------------------------------------------------------
# Forecasts
# ---------------------------------------------------------------------------
class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    department = Column(String(80), index=True)
    period_label = Column(String(40))       # e.g. "2026-2027 Q1"
    predicted_expenditure = Column(Float)
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)
    suggested_budget = Column(Float, nullable=True)
    engine = Column(String(20), default="arima")   # "arima" | "prophet" | "linear"

    generated_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="forecasts")


# ---------------------------------------------------------------------------
# Audit Chunks (RAG retrieval unit for PDF audit reports — Phase 2)
# ---------------------------------------------------------------------------
class AuditChunk(Base):
    __tablename__ = "audit_chunks"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)

    year = Column(String(20), nullable=True, index=True)
    section = Column(String(80), nullable=True, index=True)   # e.g. "Income & Expenditure"
    chunk_index = Column(Integer, default=0)
    chunk_text = Column(Text, nullable=False)

    # FAISS stores vectors in its own on-disk index; this row is the
    # authoritative metadata record for that vector (id, report, section).
    faiss_vector_id = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="audit_chunks")


# ---------------------------------------------------------------------------
# Chat history & audit log (preserved from the original system)
# ---------------------------------------------------------------------------
class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(120), nullable=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)   # JSON string of retrieved chunk refs
    query_type = Column(String(20), nullable=True)  # "sql" | "rag" | "hybrid"
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(120), nullable=True)
    action = Column(String(120), nullable=False)
    details = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)