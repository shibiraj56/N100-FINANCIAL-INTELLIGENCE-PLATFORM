"""Unit tests for NLP Pros & Cons Generator (Epic 09, Day 30)."""

import os
import unittest
import pandas as pd
from src.nlp.pros_cons_generator import ProsConsGenerator, run_pros_cons_generator


class TestProsConsGenerator(unittest.TestCase):
    """Test rule evaluations and 100% company coverage."""

    def setUp(self):
        self.generator = ProsConsGenerator()

    def test_pro_rules_logic(self):
        """Test PRO rule trigger on strong fundamental metrics."""
        r_df = pd.DataFrame([
            {"year": "2022-03", "return_on_equity_pct": 25.0, "debt_to_equity": 0.0, "free_cash_flow_cr": 500.0, "operating_profit_margin_pct": 26.0, "revenue_cagr_5yr": 16.0},
            {"year": "2023-03", "return_on_equity_pct": 26.0, "debt_to_equity": 0.0, "free_cash_flow_cr": 600.0, "operating_profit_margin_pct": 27.0, "revenue_cagr_5yr": 17.0},
            {"year": "2024-03", "return_on_equity_pct": 28.0, "debt_to_equity": 0.0, "free_cash_flow_cr": 700.0, "operating_profit_margin_pct": 28.0, "revenue_cagr_5yr": 18.0},
        ])
        pl_df = pd.DataFrame([
            {"year": "2023-03", "sales": 1000.0, "operating_profit": 270.0, "net_profit": 200.0, "eps": 20.0},
            {"year": "2024-03", "sales": 1200.0, "operating_profit": 336.0, "net_profit": 250.0, "eps": 25.0},
        ])
        bs_df = pd.DataFrame([
            {"year": "2023-03", "total_assets": 2000.0, "borrowings": 0.0},
            {"year": "2024-03", "total_assets": 2400.0, "borrowings": 0.0},
        ])

        results = self.generator.evaluate_company("TEST_STRONG", r_df, pl_df, bs_df, "Information Technology", 2.5)
        pros = [r for r in results if r["rule_type"] == "PRO"]
        self.assertTrue(len(pros) >= 3)
        rule_ids = [p["rule_id"] for p in pros]
        self.assertIn("PRO-01", rule_ids)  # ROE > 20%
        self.assertIn("PRO-03", rule_ids)  # Debt free
        self.assertIn("PRO-04", rule_ids)  # Revenue CAGR > 15%

    def test_con_rules_logic(self):
        """Test CON rule trigger on distressed/leveraged metrics."""
        r_df = pd.DataFrame([
            {"year": "2022-03", "return_on_equity_pct": 8.0, "roce_pct": 7.0, "debt_to_equity": 2.5, "free_cash_flow_cr": -500.0, "operating_profit_margin_pct": 12.0, "revenue_cagr_5yr": 3.0, "interest_coverage": 1.2},
            {"year": "2023-03", "return_on_equity_pct": 7.0, "roce_pct": 6.0, "debt_to_equity": 2.8, "free_cash_flow_cr": -600.0, "operating_profit_margin_pct": 11.0, "revenue_cagr_5yr": 2.5, "interest_coverage": 1.1},
            {"year": "2024-03", "return_on_equity_pct": 6.0, "roce_pct": 5.0, "debt_to_equity": 3.2, "free_cash_flow_cr": -700.0, "operating_profit_margin_pct": 10.0, "revenue_cagr_5yr": 2.0, "interest_coverage": 0.9, "net_debt_cr": 5000.0},
        ])
        pl_df = pd.DataFrame([
            {"year": "2023-03", "sales": 1000.0, "operating_profit": 110.0, "net_profit": 50.0, "eps": 5.0},
            {"year": "2024-03", "sales": 950.0, "operating_profit": 95.0, "net_profit": -20.0, "eps": -2.0},
        ])
        bs_df = pd.DataFrame([
            {"year": "2023-03", "total_assets": 3000.0, "borrowings": 2000.0},
            {"year": "2024-03", "total_assets": 2800.0, "borrowings": 2300.0},
        ])

        results = self.generator.evaluate_company("TEST_WEAK", r_df, pl_df, bs_df, "Industrials", 0.0)
        cons = [r for r in results if r["rule_type"] == "CON"]
        self.assertTrue(len(cons) >= 3)
        rule_ids = [c["rule_id"] for c in cons]
        self.assertIn("CON-01", rule_ids)  # D/E > 2.0
        self.assertIn("CON-04", rule_ids)  # Net loss
        self.assertIn("CON-06", rule_ids)  # ICR < 1.5

    def test_generated_csv_coverage(self):
        """CRITICAL EXIT CRITERION: Verify every company has >= 1 PRO and >= 1 CON."""
        csv_path = os.path.join("output", "pros_cons_generated.csv")
        self.assertTrue(os.path.exists(csv_path), "pros_cons_generated.csv must exist")

        df = pd.read_csv(csv_path)
        self.assertGreaterEqual(len(df), 184)  # At least 92 pros + 92 cons
        self.assertTrue((df["confidence_score"] > 60).all())

        pro_comps = set(df[df["rule_type"] == "PRO"]["company_id"])
        con_comps = set(df[df["rule_type"] == "CON"]["company_id"])
        all_comps = set(df["company_id"])

        self.assertEqual(len(all_comps), 92, "Must cover all 92 companies")
        self.assertEqual(len(pro_comps), 92, "Every company must have at least 1 PRO")
        self.assertEqual(len(con_comps), 92, "Every company must have at least 1 CON")


if __name__ == "__main__":
    unittest.main()
