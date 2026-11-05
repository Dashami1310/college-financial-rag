import unittest
from unittest.mock import patch

import pandas as pd

from app.services.query_classifier import classify_query
from app.services.rag_pipeline import answer_question
from app.services.sql_query_engine import answer_sql_question


class ChatQueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.records = pd.DataFrame([
            {
                "financial_year": "2024-2025",
                "quarter": "Q2",
                "department": "AIML",
                "budget_allocated": 1000,
                "actual_expenditure": 1200,
                "remaining_budget": -200,
                "number_of_transactions": 2,
            },
            {
                "financial_year": "2024-2025",
                "quarter": "Q2",
                "department": "CSE",
                "budget_allocated": 1500,
                "actual_expenditure": 1300,
                "remaining_budget": 200,
                "number_of_transactions": 3,
            },
            {
                "financial_year": "2025-2026",
                "quarter": "Q2",
                "department": "CSE",
                "budget_allocated": 1000,
                "actual_expenditure": 1600,
                "remaining_budget": -600,
                "number_of_transactions": 4,
            },
            {
                "financial_year": "2024",
                "quarter": "Annual",
                "department": "Institution",
                "budget_allocated": 9000,
                "actual_expenditure": 7000,
                "remaining_budget": 2000,
                "number_of_transactions": 1,
            },
        ])

    def test_quarter_filter_limits_overspend_answer(self):
        result = answer_sql_question("Which department overspent in Q2?", self.records)

        self.assertIn("AIML overspent by ₹200", result["narrative"])
        self.assertIn("CSE overspent by ₹600", result["narrative"])
        self.assertNotIn("Institution", result["narrative"])

    def test_financial_year_filter_limits_department_comparison(self):
        result = answer_sql_question(
            "Compare AIML and CSE expenditure for FY 2024-2025 Q2.",
            self.records,
        )

        self.assertIn("AIML — Budget vs Expenditure", result["narrative"])
        self.assertIn("CSE — Budget vs Expenditure", result["narrative"])
        self.assertNotIn("₹2,900", result["narrative"])

    def test_department_ranking_excludes_institution_wide_ledger(self):
        result = answer_sql_question(
            "Which department has the highest total expenditure?",
            self.records,
        )

        self.assertIn("CSE", result["narrative"])
        self.assertNotIn("Institution", result["narrative"])
        self.assertNotIn("Total Expenditure", result["narrative"])

    def test_overspend_question_uses_sql_route(self):
        self.assertEqual(classify_query("Which department overspent in Q2?"), "sql")

    def test_unrelated_question_is_classified_as_unsupported(self):
        self.assertEqual(classify_query("Why is my laptop slow?"), "unsupported")
        self.assertEqual(classify_query("Tell me a joke"), "unsupported")
        self.assertEqual(classify_query("What is the weather today?"), "unsupported")

    def test_unsupported_question_does_not_retrieve_or_generate(self):
        with (
            patch("app.services.rag_pipeline.retrieve_context") as retrieve_context,
            patch("app.services.rag_pipeline._generate_with_gemini") as generate,
        ):
            result = answer_question(
                "Why is my laptop slow?",
                user_id=1,
                transactions_df=self.records,
            )

        self.assertEqual(result["query_type"], "unsupported")
        self.assertEqual(result["generation_mode"], "out_of_scope")
        self.assertEqual(result["sources"], [])
        self.assertIn("only answer questions about", result["answer"])
        retrieve_context.assert_not_called()
        generate.assert_not_called()

    def test_financial_question_remains_supported(self):
        self.assertEqual(classify_query("Explain the audit observation"), "hybrid")
        self.assertEqual(classify_query("What is the financial position?"), "hybrid")

    def test_summary_includes_totals_and_over_budget_count(self):
        result = answer_sql_question("Summarize the financial report.", self.records)

        self.assertIn("Across 4 matching records", result["narrative"])
        self.assertIn("highest-spending department was CSE", result["narrative"])
        self.assertIn("2 record(s) exceeded", result["narrative"])

    def test_unrecognized_question_does_not_inject_unrequested_totals(self):
        result = answer_sql_question("Explain the audit observation.", self.records)

        self.assertEqual(result["figures"], [])
        self.assertEqual(result["narrative"], "")


if __name__ == "__main__":
    unittest.main()
