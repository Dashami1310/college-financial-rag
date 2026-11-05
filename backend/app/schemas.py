from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, Field


# ---------------- Auth ----------------
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = "accounts_staff"
    department: Optional[str] = None


# Kept as an alias so any existing integration/tests using "UserCreate" still work
UserCreate = SignupRequest


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    role: str
    department: Optional[str] = None
    is_active: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LogoutResponse(BaseModel):
    status: str = "logged_out"
    detail: str = "Session revoked successfully."


# ---------------- Transactions (formerly ExpenditureRecord) ----------------
class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    report_id: int
    financial_year: str
    quarter: str
    department: str
    budget_allocated: float
    actual_expenditure: float
    remaining_budget: float
    major_expense_head: Optional[str] = None
    number_of_transactions: int
    vendor: Optional[str] = None
    approval_status: Optional[str] = None
    anomalies_detected: bool
    forecast_next_quarter: Optional[float] = None


# ---------------- Dashboard ----------------
class DashboardSummary(BaseModel):
    total_budget: float
    total_income: float          # alias of total_budget — see dashboard.py note
    total_expenditure: float
    total_surplus: float
    remaining_budget: float
    budget_utilization_pct: float
    anomalies_detected: int
    active_departments: int
    total_transactions: int
    department_wise_spending: List[dict]
    quarterly_trends: List[dict]
    top_expense_heads: List[dict]
    grant_utilization: dict
    forecast_summary: dict
    anomaly_summary: dict


# ---------------- Reports ----------------
class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    report_name: str
    report_year: Optional[str] = None
    report_type: str
    status: str
    original_filename: Optional[str] = None
    row_count: int
    upload_date: datetime


class UploadResponse(BaseModel):
    report: ReportOut
    preview: List[dict]
    summary: dict
    warnings: List[str] = []


# ---------------- Analytics ----------------
class AnalyticsFilter(BaseModel):
    financial_year: Optional[str] = None
    quarter: Optional[str] = None
    department: Optional[str] = None
    report_id: Optional[int] = None


# ---------------- Anomaly ----------------
class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    transaction_id: int
    department: str
    financial_year: str
    quarter: str
    anomaly_score: float
    risk_score: float
    is_anomaly: bool
    reason: Optional[str] = None
    shap_explanation: Optional[List[dict]] = None


class AnomalyDetectionResponse(BaseModel):
    total_records_analyzed: int
    anomalies_found: int
    high_risk_departments: List[dict]
    results: List[AnomalyOut]


# ---------------- Forecasting ----------------
class ForecastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    department: str
    period_label: str
    predicted_expenditure: float
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    suggested_budget: Optional[float] = None
    engine: Optional[str] = "arima"


class ForecastResponse(BaseModel):
    department: Optional[str] = None
    history: List[dict]
    forecast: List[ForecastOut]
    annual_trend: List[dict]


# ---------------- RAG ----------------
class ChatRequest(BaseModel):
    question: str
    report_id: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    question: str
    query_type: Optional[str] = None  # "sql" | "rag" | "hybrid" | "unsupported"
    generation_mode: Optional[str] = None  # "calculated" | "extractive" | "gemini" | "out_of_scope"


# ---------------- Reports (export) ----------------
class ReportRequest(BaseModel):
    report_type: str  # "quarterly" | "department" | "summary"
    financial_year: Optional[str] = None
    quarter: Optional[str] = None
    department: Optional[str] = None
    export_format: str = "pdf"  # "pdf" | "excel"

class DatasetResponse(BaseModel):
    id: int
    name: str
    filename: str

    class Config:
        from_attributes = True