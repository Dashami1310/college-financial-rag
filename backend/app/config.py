"""
Central configuration for the
"RAG Based Financial Expenditure Analytics and Anomaly Detection System
for Technical Institution" backend.

Reads settings from environment variables / .env. PostgreSQL is now the
primary, production-grade datastore (Neon-compatible for deployment); a
local SQLite fallback is retained only so the project can still be booted
without a running Postgres instance (e.g. quick offline demos).
"""
import os
import secrets
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"          # legacy CSV/Excel dataset uploads
REPORTS_DIR = BASE_DIR / "reports_storage"  # audit PDF report storage (per-user)
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

for d in (DATA_DIR, UPLOAD_DIR, REPORTS_DIR, VECTORSTORE_DIR):
    d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    # ---- App ----
    APP_NAME: str = "RAG Based Financial Expenditure Analytics and Anomaly Detection System for Technical Institution"
    ENV: str = "development"

    # ---- Database ----
    # PostgreSQL is the primary target (works with Neon, Railway, Render,
    # local Postgres, etc.). Example:
    #   postgresql+psycopg2://user:password@host:5432/college_finance
    # Falls back to local SQLite only if DATABASE_URL is not set, so the
    # project remains runnable without any external DB for quick checks.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(DATA_DIR / 'college_finance.db').as_posix()}",
    )

    # ---- Auth ----
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours

    # ---- CORS ----
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]

    # ---- Gemini / LLM ----
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = "gemini-3.6-flash"

    # ---- RAG ----
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 80
    TOP_K: int = 6

    # ---- Anomaly Detection ----
    ISOLATION_FOREST_CONTAMINATION: float = 0.08

    # ---- Forecasting ----
    FORECAST_ENGINE: str = os.getenv("FORECAST_ENGINE", "arima")  # "arima" | "prophet"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
