from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)


def _filter_df(df: pd.DataFrame, financial_year: Optional[str], quarter: Optional[str],
                department: Optional[str]) -> pd.DataFrame:
    filtered = df.copy()
    if financial_year:
        filtered = filtered[filtered["financial_year"] == financial_year]
    if quarter:
        filtered = filtered[filtered["quarter"] == quarter]
    if department:
        filtered = filtered[filtered["department"] == department]
    return filtered


def generate_excel_report(df: pd.DataFrame, report_type: str, financial_year=None,
                           quarter=None, department=None) -> bytes:
    filtered = _filter_df(df, financial_year, quarter, department)

    summary = filtered.groupby("department").agg(
        total_budget=("budget_allocated", "sum"),
        total_expenditure=("actual_expenditure", "sum"),
        remaining_budget=("remaining_budget", "sum"),
        transactions=("number_of_transactions", "sum"),
    ).reset_index()

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="Summary")
        filtered.to_excel(writer, index=False, sheet_name="Detailed Records")
    buffer.seek(0)
    return buffer.read()


def generate_pdf_report(df: pd.DataFrame, report_type: str, financial_year=None,
                         quarter=None, department=None) -> bytes:
    filtered = _filter_df(df, financial_year, quarter, department)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleStyle", parent=styles["Title"], fontSize=18, spaceAfter=6)
    subtitle_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey)

    elements = []
    title_map = {
        "quarterly": "Quarterly Financial Report",
        "department": "Department Financial Report",
        "summary": "Financial Summary Report",
    }
    elements.append(Paragraph(title_map.get(report_type, "Financial Report"), title_style))
    subtitle = f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
    if financial_year:
        subtitle += f" | FY: {financial_year}"
    if quarter:
        subtitle += f" | Quarter: {quarter}"
    if department:
        subtitle += f" | Department: {department}"
    elements.append(Paragraph(subtitle, subtitle_style))
    elements.append(Spacer(1, 16))

    total_budget = filtered["budget_allocated"].sum()
    total_exp = filtered["actual_expenditure"].sum()
    remaining = filtered["remaining_budget"].sum()
    util = (total_exp / total_budget * 100) if total_budget else 0

    kpi_data = [
        ["Total Budget Allocated", f"₹ {total_budget:,.0f}"],
        ["Total Actual Expenditure", f"₹ {total_exp:,.0f}"],
        ["Remaining Budget", f"₹ {remaining:,.0f}"],
        ["Budget Utilization", f"{util:.1f}%"],
        ["Total Records", str(len(filtered))],
        ["Anomalies Flagged", str(int(filtered["anomalies_detected"].sum()))],
    ]
    kpi_table = Table(kpi_data, colWidths=[8 * cm, 6 * cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Department-wise Breakdown", styles["Heading2"]))
    dept_summary = filtered.groupby("department").agg(
        Budget=("budget_allocated", "sum"),
        Expenditure=("actual_expenditure", "sum"),
        Remaining=("remaining_budget", "sum"),
    ).reset_index().round(0)

    table_data = [["Department", "Budget (₹)", "Expenditure (₹)", "Remaining (₹)"]]
    for _, row in dept_summary.iterrows():
        table_data.append([
            row["department"], f"{row['Budget']:,.0f}",
            f"{row['Expenditure']:,.0f}", f"{row['Remaining']:,.0f}",
        ])

    dept_table = Table(table_data, colWidths=[5 * cm, 4 * cm, 4.5 * cm, 4 * cm])
    dept_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#14b8a6")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(dept_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
