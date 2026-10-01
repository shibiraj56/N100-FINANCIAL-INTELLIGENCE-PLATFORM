"""Unit tests for Cash Flow Intelligence Engine (Epic 07, Days 31-32)."""

import os
import unittest
import pandas as pd
from src.analytics.cashflow_kpis import (
    calculate_capex_intensity,
    calculate_cfo_quality_score,
    calculate_fcf_conversion,
    calculate_free_cash_flow,
    classify_capital_allocation,
    determine_pattern_change_type,
)


class TestCashFlowIntelligence(unittest.TestCase):
    """Test CFO quality, CapEx intensity, distress signals, and output artifacts."""

    def test_cfo_quality_score(self):
        """Test High Quality, Moderate Quality, and Accrual Risk classification."""
        # High Quality: 4 out of 5 CFO > PAT
        score, label = calculate_cfo_quality_score([120, 150, 180, 200, 90], [100, 100, 100, 100, 100])
        self.assertIn("High Quality", label)

        # Moderate Quality: 2-3 out of 5 CFO > PAT
        score, label = calculate_cfo_quality_score([120, 130, 80, 70, 60], [100, 100, 100, 100, 100])
        self.assertEqual(label, "Moderate Quality")

        # Accrual Risk: 0 or 1 out of 5 CFO > PAT
        score, label = calculate_cfo_quality_score([40, 50, 60, 70, 80], [100, 100, 100, 100, 100])
        self.assertEqual(label, "Accrual Risk")

    def test_capex_intensity(self):
        """Test Asset Light, Moderate, and Capital Intensive classification."""
        # < 3%: Asset Light
        _, lbl1 = calculate_capex_intensity(-20, 1000)
        self.assertEqual(lbl1, "Asset Light")

        # 3% - 8%: Moderate
        _, lbl2 = calculate_capex_intensity(-50, 1000)
        self.assertEqual(lbl2, "Moderate")

        # > 8%: Capital Intensive
        _, lbl3 = calculate_capex_intensity(-120, 1000)
        self.assertEqual(lbl3, "Capital Intensive")

    def test_capital_allocation_patterns(self):
        """Test classification of the 8 canonical cash flow sign patterns."""
        # (+, -, -) Shareholder Returns vs Reinvestor
        _, _, _, p1 = classify_capital_allocation(150, -50, -50, cfo_to_pat=1.2)
        self.assertEqual(p1, "Shareholder Returns")

        _, _, _, p2 = classify_capital_allocation(80, -50, -20, cfo_to_pat=0.8)
        self.assertEqual(p2, "Reinvestor")

        # (-, +, +) Distress Signal
        _, _, _, p3 = classify_capital_allocation(-50, 20, 40)
        self.assertEqual(p3, "Distress Signal")

        # (-, -, +) Growth Funded by Debt
        _, _, _, p4 = classify_capital_allocation(-50, -100, 160)
        self.assertEqual(p4, "Growth Funded by Debt")

    def test_pattern_change_types(self):
        """Test mapping pattern transitions to economic themes."""
        self.assertEqual(determine_pattern_change_type("Reinvestor", "Growth / Mixed"), "Expansion")
        self.assertEqual(determine_pattern_change_type("Growth / Mixed", "Shareholder Returns"), "Deleveraging")
        self.assertEqual(determine_pattern_change_type("Reinvestor", "Distress Signal"), "Distress")
        self.assertEqual(determine_pattern_change_type("Reinvestor", "Liquidating Assets"), "Contraction")

    def test_generated_output_files(self):
        """Verify output files: cashflow_intelligence.xlsx, distress_alerts.csv, pattern_changes.csv."""
        excel_path = os.path.join("output", "cashflow_intelligence.xlsx")
        self.assertTrue(os.path.exists(excel_path))
        df_intel = pd.read_excel(excel_path)
        self.assertEqual(len(df_intel), 92)
        self.assertIn("cfo_quality_score", df_intel.columns)
        self.assertIn("capex_intensity_label", df_intel.columns)
        self.assertIn("distress_signal", df_intel.columns)
        self.assertIn("deleveraging_flag", df_intel.columns)

        distress_path = os.path.join("output", "distress_alerts.csv")
        self.assertTrue(os.path.exists(distress_path))
        df_distress = pd.read_csv(distress_path)
        self.assertGreaterEqual(len(df_distress), 1)

        pattern_path = os.path.join("output", "pattern_changes.csv")
        self.assertTrue(os.path.exists(pattern_path))
        df_pattern = pd.read_csv(pattern_path)
        self.assertGreaterEqual(len(df_pattern), 1)


if __name__ == "__main__":
    unittest.main()
