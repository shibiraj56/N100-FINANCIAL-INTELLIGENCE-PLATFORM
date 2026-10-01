"""Unit tests for Institutional PDF Report Generation (Epic 08, Days 33-35)."""

import os
import sqlite3
import unittest
import pandas as pd
from pypdf import PdfReader
from src.reports.tearsheet import TearsheetGenerator, DEFAULT_DB_PATH
from src.reports.sector_report import SectorReportGenerator, sanitize_filename
from src.reports.portfolio_report import PortfolioReportGenerator


class TestPDFReportGeneration(unittest.TestCase):
    """Test tearsheets, sector reports, and portfolio compendium."""

    @classmethod
    def setUpClass(cls):
        cls.conn = sqlite3.connect(DEFAULT_DB_PATH)
        cls.comps = pd.read_sql("SELECT id FROM companies ORDER BY id", cls.conn)["id"].tolist()
        cls.peer_groups = pd.read_sql("SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY peer_group_name", cls.conn)[
            "peer_group_name"
        ].tolist()
        cls.conn.close()

    def test_single_tearsheet_structure_and_constraints(self):
        """Test tearsheet generation meets strict 2-page and >=30KB requirements."""
        gen = TearsheetGenerator()
        out_pdf = os.path.join("reports", "tearsheets", "TCS_tearsheet.pdf")
        gen.generate("TCS", out_pdf)

        self.assertTrue(os.path.exists(out_pdf))
        sz = os.path.getsize(out_pdf)
        self.assertGreaterEqual(sz, 30_000, f"File size {sz} must be >= 30,000 bytes")

        reader = PdfReader(out_pdf)
        self.assertEqual(len(reader.pages), 2, "Tearsheet must be strictly 2 pages")

    def test_all_92_tearsheets_exist_and_valid(self):
        """Verify all 92 company tearsheets exist, are >= 30KB, and have 2 pages."""
        tearsheet_dir = os.path.join("reports", "tearsheets")
        self.assertTrue(os.path.exists(tearsheet_dir))

        failed_files = []
        for ticker in self.comps:
            pdf_path = os.path.join(tearsheet_dir, f"{ticker}_tearsheet.pdf")
            if not os.path.exists(pdf_path):
                failed_files.append((ticker, "Missing file"))
                continue
            sz = os.path.getsize(pdf_path)
            if sz < 30_000:
                failed_files.append((ticker, f"Size too small: {sz} bytes"))
                continue
            reader = PdfReader(pdf_path)
            if len(reader.pages) != 2:
                failed_files.append((ticker, f"Invalid page count: {len(reader.pages)} pages"))

        self.assertEqual(
            len(failed_files),
            0,
            f"Some tearsheets failed validation: {failed_files[:5]}",
        )

    def test_all_11_sector_reports_exist(self):
        """Verify all 11 sector peer group reports exist and have content."""
        sector_dir = os.path.join("reports", "sector")
        self.assertTrue(os.path.exists(sector_dir))

        self.assertEqual(len(self.peer_groups), 11, "Must have exactly 11 peer groups")
        for pg in self.peer_groups:
            fname = f"{sanitize_filename(pg)}_report.pdf"
            pdf_path = os.path.join(sector_dir, fname)
            self.assertTrue(os.path.exists(pdf_path), f"Sector report {fname} missing")
            sz = os.path.getsize(pdf_path)
            self.assertGreater(sz, 15_000, f"Sector report {fname} too small: {sz} bytes")
            reader = PdfReader(pdf_path)
            self.assertGreaterEqual(len(reader.pages), 1)

    def test_portfolio_summary_report_exists(self):
        """Verify portfolio summary compendium report exists and has valid pages."""
        port_pdf = os.path.join("reports", "portfolio", "portfolio_summary.pdf")
        self.assertTrue(os.path.exists(port_pdf), "portfolio_summary.pdf missing")
        sz = os.path.getsize(port_pdf)
        self.assertGreater(sz, 10_000, f"Portfolio report too small: {sz} bytes")
        reader = PdfReader(port_pdf)
        self.assertGreaterEqual(len(reader.pages), 2)


if __name__ == "__main__":
    unittest.main()
