"""Unit tests for NLP Analysis Text Parser (Epic 09, Day 29)."""

import os
import unittest
from src.nlp.parser import CAGR_REGEX, AnalysisParser


class TestNLPParser(unittest.TestCase):
    """Test regex extraction and parsing of growth metrics."""

    def test_regex_matching_standard(self):
        """Test standard period and percentage formats."""
        m1 = CAGR_REGEX.search("10 Years: 21%")
        self.assertIsNotNone(m1)
        self.assertEqual(m1.group(1), "10")
        self.assertEqual(m1.group(2), "21")

        m2 = CAGR_REGEX.search("5 Years: 13.5%")
        self.assertIsNotNone(m2)
        self.assertEqual(m2.group(1), "5")
        self.assertEqual(m2.group(2), "13.5")

        m3 = CAGR_REGEX.search("1 Year: -4.2%")
        self.assertIsNotNone(m3)
        self.assertEqual(m3.group(1), "1")
        self.assertEqual(m3.group(2), "-4.2")

    def test_regex_multiline_string(self):
        """Test extraction of multiple period metrics from a multi-line string."""
        sample_text = (
            "Compounded Profit Growth:\n"
            "10 Years: 15%\n"
            "5 Years: 18%\n"
            "3 Years: 22%\n"
            "TTM: 25%"
        )
        matches = CAGR_REGEX.findall(sample_text)
        self.assertEqual(len(matches), 3)
        self.assertEqual(matches[0], ("10", "15"))
        self.assertEqual(matches[1], ("5", "18"))
        self.assertEqual(matches[2], ("3", "22"))

    def test_parse_entry_valid(self):
        """Test parser method for valid multi-line field."""
        parser = AnalysisParser()
        parser.parse_entry(
            company_id="TCS",
            field_name="compounded_sales_growth",
            metric_type="sales_cagr",
            text="10 Years: 12%\n5 Years: 14%",
        )
        self.assertEqual(len(parser.parsed_records), 2)
        self.assertEqual(parser.parsed_records[0]["company_id"], "TCS")
        self.assertEqual(parser.parsed_records[0]["period_years"], 10)
        self.assertEqual(parser.parsed_records[0]["value_pct"], 12.0)
        self.assertEqual(parser.parsed_records[1]["period_years"], 5)
        self.assertEqual(parser.parsed_records[1]["value_pct"], 14.0)

    def test_parse_entry_failure_logging(self):
        """Test unparseable strings logged to failures."""
        parser = AnalysisParser()
        parser.parse_entry(
            company_id="TESTCO",
            field_name="compounded_sales_growth",
            metric_type="sales_cagr",
            text="No historical growth data available for TTM period",
        )
        self.assertEqual(len(parser.parsed_records), 0)
        self.assertEqual(len(parser.failures), 1)
        self.assertEqual(parser.failures[0]["company_id"], "TESTCO")


if __name__ == "__main__":
    unittest.main()
