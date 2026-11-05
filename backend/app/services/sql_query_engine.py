from __future__ import annotations

import re
from typing import Dict, Optional

import pandas as pd


def total_income(df: pd.DataFrame) -> Dict:
    value = float(df["budget_allocated"].sum()) if not df.empty else 0.0
    return {"label": "Total Income (Budget Allocated)", "value": value}


def total_expenditure(df: pd.DataFrame) -> Dict:
    value = float(df["actual_expenditure"].sum()) if not df.empty else 0.0
    return {"label": "Total Expenditure", "value": value}


def total_surplus(df: pd.DataFrame) -> Dict:
    income = total_income(df)["value"]
    expenditure = total_expenditure(df)["value"]
    return {"label": "Total Surplus (Income - Expenditure)", "value": income - expenditure}


def highest_spending_department(df: pd.DataFrame) -> Optional[Dict]:
    if df.empty:
        return None
    grouped = df.groupby("department")["actual_expenditure"].sum()
    dept = grouped.idxmax()
    return {"label": "Highest Spending Department", "department": dept, "value": float(grouped[dept])}


def lowest_spending_department(df: pd.DataFrame) -> Optional[Dict]:
    if df.empty:
        return None
    grouped = df.groupby("department")["actual_expenditure"].sum()
    dept = grouped.idxmin()
    return {"label": "Lowest Spending Department", "department": dept, "value": float(grouped[dept])}


def average_expenditure(df: pd.DataFrame) -> Dict:
    value = float(df["actual_expenditure"].mean()) if not df.empty else 0.0
    return {"label": "Average Expenditure per Record", "value": value}


def department_total(df: pd.DataFrame, department: str) -> Optional[Dict]:
    subset = df[df["department"].str.lower() == department.lower()]
    if subset.empty:
        return None
    return {
        "label": f"{department} — Budget vs Expenditure",
        "budget_allocated": float(subset["budget_allocated"].sum()),
        "actual_expenditure": float(subset["actual_expenditure"].sum()),
        "remaining_budget": float(subset["remaining_budget"].sum()),
    }


def remaining_budget(df: pd.DataFrame) -> Dict:
    value = float(df["remaining_budget"].sum()) if not df.empty else 0.0
    return {"label": "Total Remaining Budget", "value": value}


def transaction_count(df: pd.DataFrame) -> Dict:
    value = int(df["number_of_transactions"].sum()) if not df.empty else 0
    return {"label": "Total Number of Transactions", "value": value}


def _filter_question_period(question: str, df: pd.DataFrame) -> pd.DataFrame:
    filtered = df
    quarter_match = re.search(r"\bq([1-4])\b", question, re.IGNORECASE)
    if quarter_match:
        filtered = filtered[
            filtered["quarter"].astype(str).str.upper() == f"Q{quarter_match.group(1)}"
        ]

    year_match = re.search(
        r"\b(?:fy\s*)?(20\d{2})\s*[-–/]\s*(20\d{2}|\d{2})\b",
        question,
        re.IGNORECASE,
    )
    if year_match:
        start, end = year_match.groups()
        if len(end) == 2:
            end = start[:2] + end
        financial_year = f"{start}-{end}"
        filtered = filtered[filtered["financial_year"].astype(str) == financial_year]
    else:
        year_match = re.search(r"\b(?:fy|in|during|for)\s+(20\d{2})\b", question, re.IGNORECASE)
        if year_match:
            year = year_match.group(1)
            filtered = filtered[
                filtered["financial_year"].astype(str).str.startswith(year)
            ]

    return filtered


def _department_spending(df: pd.DataFrame) -> pd.Series:
    return (
        df[df["department"].astype(str).str.casefold() != "institution"]
        .groupby("department")["actual_expenditure"]
        .sum()
        .sort_values(ascending=False)
    )


def _format_money(value: float) -> str:
    return f"₹{value:,.0f}"


# ---------------------------------------------------------------------------
# Dispatcher — inspects the question text to pick the right computation(s)
# ---------------------------------------------------------------------------
def answer_sql_question(question: str, df: pd.DataFrame) -> Dict:
    """
    Returns {"figures": [ {label, value/department/...}, ... ], "narrative": str}
    `figures` is a list because some questions imply more than one number
    (e.g. "surplus" implicitly needs income and expenditure shown too).
    """
    q = question.casefold()
    scoped_df = _filter_question_period(question, df)
    if scoped_df.empty:
        return {
            "figures": [],
            "narrative": "No uploaded records match the requested period.",
        }

    departments = sorted(
        scoped_df["department"].dropna().astype(str).unique(),
        key=len,
        reverse=True,
    )
    mentioned_departments = [
        department for department in departments
        if re.search(rf"(?<!\w){re.escape(department)}(?!\w)", question, re.IGNORECASE)
    ]

    quarter_match = re.search(r"\bq([1-4])\b", question, re.IGNORECASE)
    year_match = re.search(
        r"\b(?:fy\s*)?(20\d{2})\s*[-–/]\s*(20\d{2}|\d{2})\b",
        question,
        re.IGNORECASE,
    )
    period = ""
    if year_match:
        start, end = year_match.groups()
        period = f" for FY {start}-{end if len(end) == 4 else start[:2] + end}"
    elif re.search(r"\b(?:fy|in|during|for)\s+20\d{2}\b", question, re.IGNORECASE):
        year = re.search(r"\b(?:fy|in|during|for)\s+(20\d{2})\b", question, re.IGNORECASE).group(1)
        period = f" for {year}"
    if quarter_match:
        period += f" Q{quarter_match.group(1)}"

    figures = []

    if re.search(r"\b(summarize|summarise|summary|overview)\b", q):
        budget = float(scoped_df["budget_allocated"].sum())
        expenditure = float(scoped_df["actual_expenditure"].sum())
        ranked_departments = _department_spending(scoped_df)
        over_budget_count = int(
            (
                (pd.to_numeric(scoped_df["budget_allocated"], errors="coerce") > 0)
                & (
                    pd.to_numeric(scoped_df["actual_expenditure"], errors="coerce")
                    > pd.to_numeric(scoped_df["budget_allocated"], errors="coerce")
                )
            ).sum()
        )
        figures = [
            {"label": "Total Budget Allocated", "value": budget},
            {"label": "Total Expenditure", "value": expenditure},
            {"label": "Remaining Budget", "value": budget - expenditure},
        ]
        summary_parts = [
            f"Across {len(scoped_df):,} matching records{period}, "
            f"total budget allocated was {_format_money(budget)} and "
            f"expenditure was {_format_money(expenditure)} "
            f"(remaining budget {_format_money(budget - expenditure)})."
        ]
        if not ranked_departments.empty:
            summary_parts.append(
                f"The highest-spending department was {ranked_departments.index[0]} "
                f"at {_format_money(float(ranked_departments.iloc[0]))}."
            )
        summary_parts.append(f"{over_budget_count:,} record(s) exceeded their allocated budget.")
        return {"figures": figures, "narrative": " ".join(summary_parts)}

    if re.search(r"\b(over[- ]?spent|overspend|overspent|over budget|budget violation)\b", q):
        overspend_rows = scoped_df[
            (pd.to_numeric(scoped_df["budget_allocated"], errors="coerce") > 0)
            & (
                pd.to_numeric(scoped_df["actual_expenditure"], errors="coerce")
                > pd.to_numeric(scoped_df["budget_allocated"], errors="coerce")
            )
        ].copy()
        if mentioned_departments:
            overspend_rows = overspend_rows[
                overspend_rows["department"].isin(mentioned_departments)
            ]
        if overspend_rows.empty:
            return {
                "figures": [],
                "narrative": f"No departments exceeded their allocated budget{period}.",
            }
        grouped = overspend_rows.groupby("department").agg(
            budget=("budget_allocated", "sum"),
            expenditure=("actual_expenditure", "sum"),
        )
        grouped["overspend"] = grouped["expenditure"] - grouped["budget"]
        grouped = grouped.sort_values("overspend", ascending=False)
        figures = [
            {"department": department, **row.to_dict()}
            for department, row in grouped.iterrows()
        ]
        narrative = "; ".join(
            f"{row['department']} overspent by {_format_money(row['overspend'])} "
            f"(budget {_format_money(row['budget'])}; expenditure {_format_money(row['expenditure'])})"
            for row in figures
        )
        return {"figures": figures, "narrative": f"Departments over budget{period}: {narrative}."}

    if len(mentioned_departments) >= 2 and re.search(r"\b(compare|comparison|versus|vs\.?)\b", q):
        for department in mentioned_departments:
            result = department_total(scoped_df, department)
            if result:
                figures.append(result)
        narrative = "; ".join(
            f"{figure['label']}: budget {_format_money(figure['budget_allocated'])}, "
            f"expenditure {_format_money(figure['actual_expenditure'])}, "
            f"remaining {_format_money(figure['remaining_budget'])}"
            for figure in figures
        )
        return {"figures": figures, "narrative": f"Department comparison{period}: {narrative}."}

    if mentioned_departments:
        result = department_total(scoped_df, mentioned_departments[0])
        if result:
            figures.append(result)

    ranking_requested = bool(
        re.search(r"\b(lowest|least|minimum|min|highest|most|maximum|max|top department|which department)\b", q)
    )
    if re.search(r"\b(total\s+surplus|surplus)\b", q):
        figures.extend([total_income(scoped_df), total_expenditure(scoped_df), total_surplus(scoped_df)])
    elif re.search(r"\b(total\s+income|total\s+budget|budget allocated)\b", q):
        figures.append(total_income(scoped_df))
    elif (
        not ranking_requested
        and re.search(r"\b(total\s+expenditure|how much (?:was )?(?:spent|expended))\b", q)
    ):
        figures.append(total_expenditure(scoped_df))

    spending = _department_spending(scoped_df)
    if re.search(r"\b(lowest|least|minimum|min)\b", q):
        if not spending.empty:
            department = spending.index[-1]
            figures.append({"label": "Lowest Spending Department", "department": department, "value": float(spending.iloc[-1])})
    elif re.search(r"\b(highest|most|maximum|max|top department|which department)\b", q):
        if not spending.empty:
            department = spending.index[0]
            figures.append({"label": "Highest Spending Department", "department": department, "value": float(spending.iloc[0])})

    if re.search(r"\baverage\b", q):
        figures.append(average_expenditure(scoped_df))
    if re.search(r"\bremaining budget\b", q):
        figures.append(remaining_budget(scoped_df))
    if re.search(r"\bhow many transactions?\b", q):
        figures.append(transaction_count(scoped_df))

    if re.search(r"\bwhich quarter\b|\bquarter.*(?:highest|most|maximum)\b", q):
        quarterly = scoped_df.groupby("quarter")["actual_expenditure"].sum()
        quarterly = quarterly.drop(index="Annual", errors="ignore")
        if not quarterly.empty:
            quarter = quarterly.idxmax()
            return {
                "figures": [{"quarter": quarter, "value": float(quarterly[quarter])}],
                "narrative": f"{quarter} had the highest expenditure{period}: {_format_money(float(quarterly[quarter]))}.",
            }

    if not figures:
        return {"figures": [], "narrative": ""}

    narrative_parts = []
    for figure in figures:
        if "department" in figure and "budget_allocated" not in figure:
            narrative_parts.append(
                f"{figure['label']}: {figure['department']} ({_format_money(figure['value'])})"
            )
        elif "budget_allocated" in figure:
            narrative_parts.append(
                f"{figure['label']} — Budget: {_format_money(figure['budget_allocated'])}, "
                f"Expenditure: {_format_money(figure['actual_expenditure'])}, "
                f"Remaining: {_format_money(figure['remaining_budget'])}"
            )
        else:
            narrative_parts.append(f"{figure['label']}: {_format_money(figure['value'])}")

    return {"figures": figures, "narrative": f"{'; '.join(narrative_parts)}{period}."}
