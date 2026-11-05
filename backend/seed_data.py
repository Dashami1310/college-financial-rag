"""
Seed script for local development / demo purposes.

"RAG Based Financial Expenditure Analytics and Anomaly Detection System
for Technical Institution"

Creates:
  1. Database tables (via Alembic-managed schema — run `alembic upgrade head`
     BEFORE this script; this script only inserts rows, it does not create
     tables itself, matching a normal Postgres migration workflow)
  2. Demo users for each role (admin, accounts_staff, hod, principal)
  3. TWO owned sample Reports per demo user — one per financial year
     (2024-2025 and 2025-2026), each a separate, independently-selectable
     report covering all 12 departments across 4 quarters — so the
     year-wise dashboard ("click a year, see that year's numbers") has
     more than one year to demonstrate out of the box. Each report is
     imported as its own set of `Transaction` rows, plus a per-user FAISS
     index spanning both years for the RAG assistant.

Run (after `alembic upgrade head`):
    python seed_data.py
"""
import random
from pathlib import Path

import numpy as np
import pandas as pd

from app.database import SessionLocal
from app import models
from app.auth import hash_password
from app.services import data_processing
from app.services.rag_pipeline import build_vectorstore_for_user

random.seed(42)
np.random.seed(42)

DEPARTMENTS = [
    "AIML", "CSE", "ISE", "ECE", "EEE", "Mechanical", "Civil",
    "Biotechnology", "Chemical", "Textile", "MBA", "MCA",
    "Library", "Administration", "Training & Placement",
]

EXPENSE_HEADS = [
    "Salaries", "Laboratory Equipment", "Infrastructure Maintenance",
    "Events & Workshops", "Software Licenses", "Travel & Conferences",
    "Library Resources", "Furniture", "Utilities", "Research Grants",
]

VENDORS = [
    "TechSupply Pvt Ltd", "Karnataka Electricals", "CampusBuild Contractors",
    "EduSoft Solutions", "National Book Depot", "PowerLine Traders",
    "Global Lab Instruments", "Prime Furnishings", "NetConnect Services",
]

# Two consecutive financial years, seeded as two SEPARATE reports so the
# year-wise dashboard has real multi-year data to switch between.
FINANCIAL_YEARS = ["2024-2025", "2025-2026"]
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]

BASE_BUDGET = {
    "AIML": 1_800_000, "CSE": 2_200_000, "ISE": 1_600_000, "ECE": 1_700_000,
    "EEE": 1_500_000, "Mechanical": 1_900_000, "Civil": 1_650_000,
    "Biotechnology": 1_100_000, "Chemical": 1_050_000, "Textile": 850_000,
    "MBA": 1_200_000, "MCA": 1_150_000,
    "Library": 900_000, "Administration": 2_500_000, "Training & Placement": 700_000,
}

# Year-over-year growth factor so 2025-2026 isn't just a copy of 2024-2025
# (more realistic for a "compare year to year" demo).
YEAR_GROWTH = {"2024-2025": 1.0, "2025-2026": 1.08}


def generate_sample_dataframe(financial_year: str) -> pd.DataFrame:
    growth = YEAR_GROWTH.get(financial_year, 1.0)
    rows = []
    for dept in DEPARTMENTS:
        base = BASE_BUDGET[dept] * growth
        for q in QUARTERS:
            seasonal_factor = {"Q1": 0.9, "Q2": 1.05, "Q3": 1.15, "Q4": 0.95}[q]
            quarterly_budget = round(base / 4 * seasonal_factor * random.uniform(0.95, 1.05), -2)

            is_anomaly_row = random.random() < 0.08
            utilization = random.uniform(1.25, 1.8) if is_anomaly_row else random.uniform(0.65, 1.05)

            expenditure = round(quarterly_budget * utilization, -2)
            remaining = quarterly_budget - expenditure
            transactions = random.randint(15, 120)
            head = random.choice(EXPENSE_HEADS)
            vendor = random.choice(VENDORS)
            status = "Approved" if remaining >= 0 or random.random() > 0.3 else "Pending"

            rows.append({
                "financial_year": financial_year,
                "quarter": q,
                "department": dept,
                "budget_allocated": quarterly_budget,
                "actual_expenditure": expenditure,
                "remaining_budget": remaining,
                "major_expense_head": head,
                "number_of_transactions": transactions,
                "vendor": vendor,
                "approval_status": status,
                "anomalies_detected": is_anomaly_row,
                "forecast_next_quarter": None,
            })
    return pd.DataFrame(rows)


def seed_users(db):
    demo_users = [
        {"name": "System Administrator", "email": "admin@college.edu",
         "password": "Admin@123", "role": "admin", "department": None},
        {"name": "Accounts Staff", "email": "accounts@college.edu",
         "password": "Accounts@123", "role": "accounts_staff", "department": "Administration"},
        {"name": "Dr. HOD AIML", "email": "hod.aiml@college.edu",
         "password": "Hod@123", "role": "hod", "department": "AIML"},
        {"name": "Principal", "email": "principal@college.edu",
         "password": "Principal@123", "role": "principal", "department": None},
    ]
    created = []
    for u in demo_users:
        existing = db.query(models.User).filter(models.User.email == u["email"]).first()
        if existing:
            created.append(existing)
            continue
        user = models.User(
            name=u["name"], email=u["email"],
            password_hash=hash_password(u["password"]),
            role=u["role"], department=u["department"],
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        created.append(user)
    print("Demo users seeded (see credentials printed at the end).")
    return created


def seed_sample_reports_for_user(db, user: models.User):
    existing = db.query(models.Report).filter(models.Report.user_id == user.id).first()
    if existing:
        print(f"  - {user.email}: sample reports already present, skipping.")
        return

    for financial_year in FINANCIAL_YEARS:
        df = generate_sample_dataframe(financial_year)

        safe_year = financial_year.replace("/", "-")
        out_path = Path(__file__).parent / "app" / "data" / f"sample_{user.id}_{safe_year}.csv"
        df.to_csv(out_path, index=False)

        clean_df = data_processing.clean_dataset(df)

        report = models.Report(
            user_id=user.id,
            report_name=f"College Financial Data {financial_year}",
            report_year=financial_year,
            report_type=models.ReportType.CSV,
            status=models.ReportStatus.READY,
            file_path=str(out_path),
            original_filename=out_path.name,
            row_count=len(clean_df),
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        data_processing.persist_transactions(db, clean_df, report, user.id)
        print(f"  - {user.email}: seeded report #{report.id} ({financial_year}) with {len(clean_df)} transactions.")

    try:
        build_vectorstore_for_user(db, user_id=user.id)
        print(f"  - {user.email}: FAISS index built (spanning both years).")
    except Exception as e:
        print(f"  - {user.email}: [WARN] vector store build skipped ({e})")


def main():
    print("Initializing database session (schema must already exist — run "
          "`alembic upgrade head` first)...")
    db = SessionLocal()
    try:
        users = seed_users(db)
        print("\nSeeding two sample reports (2024-2025 and 2025-2026) per demo user:")
        for user in users:
            seed_sample_reports_for_user(db, user)
    finally:
        db.close()

    print("\nSeeding complete. Start the API with:")
    print("  uvicorn app.main:app --reload --port 8000\n")
    print("Demo login credentials:")
    print("  Admin          -> admin@college.edu / Admin@123")
    print("  Accounts Staff -> accounts@college.edu / Accounts@123")
    print("  HOD (AIML)     -> hod.aiml@college.edu / Hod@123")
    print("  Principal      -> principal@college.edu / Principal@123")


if __name__ == "__main__":
    main()
