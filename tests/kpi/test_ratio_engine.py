"""Integration tests for Ratio Engine, DB persistence, screener preview, and edge cases (Day 14)."""

import os
from pathlib import Path
import sqlite3
import pandas as pd
import pytest

from src.analytics.ratio_engine import RatioEngine

DB_PATH = "data/nifty100.db"


@pytest.fixture(scope="module")
def db_conn():
    # Ensure Ratio Engine has processed the database
    RatioEngine(db_path=DB_PATH).run()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()


def test_financial_ratios_row_count(db_conn):
    """Verify financial_ratios has >= 1,100 rows (acceptance criterion)."""
    count = db_conn.execute("SELECT COUNT(*) FROM financial_ratios").fetchone()[0]
    assert count >= 1100, f"Expected >= 1100 rows, got {count}"


def test_financial_ratios_all_92_companies(db_conn):
    """Verify all 92 companies have ratio records."""
    count = db_conn.execute(
        "SELECT COUNT(DISTINCT company_id) FROM financial_ratios"
    ).fetchone()[0]
    assert count == 92, f"Expected 92 companies, got {count}"


def test_no_null_only_columns(db_conn):
    """Verify no column in financial_ratios contains only NULL values."""
    cursor = db_conn.cursor()
    cursor.execute("PRAGMA table_info(financial_ratios)")
    cols = [c[1] for c in cursor.fetchall()]
    for col in cols:
        non_null_count = db_conn.execute(
            f"SELECT COUNT(*) FROM financial_ratios WHERE {col} IS NOT NULL"
        ).fetchone()[0]
        assert non_null_count > 0, f"Column {col} is completely NULL!"


def test_financials_sector_carveout(db_conn):
    """Verify that all 23 Financials sector companies have high_leverage_flag = 0."""
    fin_companies = [
        r[0]
        for r in db_conn.execute(
            "SELECT company_id FROM sectors WHERE LOWER(broad_sector) = 'financials'"
        ).fetchall()
    ]
    assert len(fin_companies) == 23, f"Expected 23 Financials companies, got {len(fin_companies)}"

    placeholders = ",".join(f"'{cid}'" for cid in fin_companies)
    flagged_count = db_conn.execute(
        f"SELECT COUNT(*) FROM financial_ratios WHERE company_id IN ({placeholders}) AND high_leverage_flag = 1"
    ).fetchone()[0]
    assert flagged_count == 0, f"Expected 0 high_leverage_flags for Financials, got {flagged_count}"


def test_screener_preview_roe_de(db_conn):
    """Verify screener preview (ROE > 15% AND D/E < 1) returns between 15 and 50 companies."""
    count = db_conn.execute(
        """
        SELECT COUNT(DISTINCT company_id)
        FROM financial_ratios
        WHERE year = '2024-03'
          AND return_on_equity_pct > 15.0
          AND debt_to_equity < 1.0
        """
    ).fetchone()[0]
    assert 15 <= count <= 50, f"Expected between 15 and 50 companies, got {count}"


def test_spot_check_tcs_roe(db_conn):
    """Spot-check TCS ROE: true value is ~50.94%, resolving source 0.52% anomaly."""
    roe = db_conn.execute(
        "SELECT return_on_equity_pct FROM financial_ratios WHERE company_id = 'TCS' AND year = '2024-03'"
    ).fetchone()[0]
    assert roe is not None
    assert 48.0 <= roe <= 53.0, f"Expected TCS ROE around 50.94%, got {roe}"


def test_spot_check_infy_cagr(db_conn):
    """Spot-check INFY 5-year sales CAGR: verified at 13.20%."""
    cagr = db_conn.execute(
        "SELECT revenue_cagr_5yr FROM financial_ratios WHERE company_id = 'INFY' AND year = '2024-03'"
    ).fetchone()[0]
    assert cagr is not None
    assert round(cagr, 1) == 13.2, f"Expected INFY 5Y Revenue CAGR 13.2%, got {cagr}"


def test_spot_check_reliance_cagr(db_conn):
    """Spot-check RELIANCE 5-year sales CAGR: verified at 9.61%."""
    cagr = db_conn.execute(
        "SELECT revenue_cagr_5yr FROM financial_ratios WHERE company_id = 'RELIANCE' AND year = '2024-03'"
    ).fetchone()[0]
    assert cagr is not None
    assert round(cagr, 1) == 9.6, f"Expected RELIANCE 5Y Revenue CAGR 9.61%, got {cagr}"


def test_capital_allocation_artifacts(db_conn):
    """Verify capital_allocation table and CSV exports."""
    db_count = db_conn.execute("SELECT COUNT(*) FROM capital_allocation").fetchone()[0]
    assert db_count >= 1000

    csv_path = Path("output/capital_allocation.csv")
    assert csv_path.exists()
    df_ca = pd.read_csv(csv_path)
    assert len(df_ca) == db_count
    assert "pattern_label" in df_ca.columns


def test_ratio_edge_cases_log():
    """Verify ratio_edge_cases.log existence and expected category contents."""
    log_file = Path("output/ratio_edge_cases.log")
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "[FINANCIALS CARVE-OUT]" in content
    assert "[DATA SOURCE ISSUE]" in content
    assert "[DEBT FREE SUBSTITUTION]" in content
    assert "[CAGR ANOMALY / TURNAROUND]" in content
    assert "TCS" in content
