"""Unit tests for all 14 Data Quality Rules (DQ-01 to DQ-14) (Day 21)."""

import pandas as pd
import pytest
from src.etl.validator import DataValidator


def test_dq01_company_pk_uniqueness():
    """DQ-01: Company PK Uniqueness (CRITICAL)."""
    df_co = pd.DataFrame({"id": ["TCS", "INFY", "TCS"]})
    validator = DataValidator({"companies": df_co})
    validator._check_dq01_company_pk_uniqueness()
    assert len(validator.failures) == 2
    assert validator.failures[0]["rule_id"] == "DQ-01"
    assert validator.failures[0]["severity"] == "CRITICAL"


def test_dq02_annual_pk_uniqueness():
    """DQ-02: Annual PK Uniqueness (CRITICAL)."""
    df_pl = pd.DataFrame({
        "company_id": ["TCS", "TCS"],
        "year": ["2024-03", "2024-03"],
        "sales": [100.0, 105.0]
    })
    validator = DataValidator({"profitandloss": df_pl})
    validator._check_dq02_annual_pk_uniqueness()
    assert len(validator.failures) == 2
    assert validator.failures[0]["rule_id"] == "DQ-02"


def test_dq03_fk_integrity():
    """DQ-03: Foreign Key Integrity (CRITICAL)."""
    df_co = pd.DataFrame({"id": ["TCS", "INFY"]})
    df_pl = pd.DataFrame({
        "company_id": ["TCS", "UNKNOWN_CO"],
        "year": ["2024-03", "2024-03"],
    })
    validator = DataValidator({"companies": df_co, "profitandloss": df_pl})
    validator._check_dq03_fk_integrity()
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "UNKNOWN_CO"


def test_dq04_bs_balance():
    """DQ-04: Balance Sheet Equality."""
    df_bs = pd.DataFrame({
        "company_id": ["TCS", "INFY"],
        "year": ["2024-03", "2024-03"],
        "total_assets": [1000.0, 1000.0],
        "total_liabilities": [1000.0, 1020.0],
    })
    validator = DataValidator({"balancesheet": df_bs})
    validator._check_dq04_bs_balance()
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "INFY"


def test_dq05_opm_cross_check():
    """DQ-05: OPM Cross-Check."""
    df_pl = pd.DataFrame({
        "company_id": ["TCS"],
        "year": ["2024-03"],
        "sales": [100.0],
        "operating_profit": [20.0],
        "opm_percentage": [15.0],  # Difference = 5% > 1%
    })
    validator = DataValidator({"profitandloss": df_pl})
    validator._check_dq05_opm_cross_check()
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-05"


def test_dq06_positive_sales():
    """DQ-06: Non-negative Sales."""
    df_pl = pd.DataFrame({
        "company_id": ["TCS", "LOSSCO"],
        "year": ["2024-03", "2024-03"],
        "sales": [100.0, 0.0],
    })
    validator = DataValidator({"profitandloss": df_pl})
    validator._check_dq06_positive_sales()
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "LOSSCO"


def test_dq07_year_format():
    """DQ-07: Year Format (YYYY-MM)."""
    df_pl = pd.DataFrame({
        "company_id": ["TCS", "INFY"],
        "year": ["2024-03", "invalid_year"],
    })
    validator = DataValidator({"profitandloss": df_pl})
    validator._check_dq07_year_format()
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-07"


def test_dq08_ticker_format():
    """DQ-08: Ticker Format."""
    df_co = pd.DataFrame({"id": ["TCS", "bad ticker!"]})
    validator = DataValidator({"companies": df_co})
    validator._check_dq08_ticker_format()
    assert len(validator.failures) == 1
    assert validator.failures[0]["rule_id"] == "DQ-08"


def test_dq09_net_cash():
    """DQ-09: Cash Flow Arithmetic."""
    df_cf = pd.DataFrame({
        "company_id": ["TCS", "DIFFCO"],
        "year": ["2024-03", "2024-03"],
        "operating_activity": [100.0, 100.0],
        "investing_activity": [-50.0, -50.0],
        "financing_activity": [-30.0, -30.0],
        "net_cash_flow": [20.0, 50.0],  # 100 - 50 - 30 = 20 != 50
    })
    validator = DataValidator({"cashflow": df_cf})
    validator._check_dq09_net_cash()
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "DIFFCO"


def test_dq10_fixed_assets():
    """DQ-10: Non-Negative Fixed Assets."""
    df_bs = pd.DataFrame({
        "company_id": ["TCS", "NEGCO"],
        "year": ["2024-03", "2024-03"],
        "fixed_assets": [100.0, -5.0],
    })
    validator = DataValidator({"balancesheet": df_bs})
    validator._check_dq10_fixed_assets()
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "NEGCO"


def test_dq11_tax_rate():
    """DQ-11: Tax Rate Bounds (0% to 50%)."""
    df_pl = pd.DataFrame({
        "company_id": ["TCS", "HIGHTAX"],
        "year": ["2024-03", "2024-03"],
        "tax_percentage": [25.0, 75.0],
    })
    validator = DataValidator({"profitandloss": df_pl})
    validator._check_dq11_tax_rate()
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "HIGHTAX"


def test_dq12_dividend_cap():
    """DQ-12: Dividend Payout Cap (>100%)."""
    df_pl = pd.DataFrame({
        "company_id": ["TCS", "OVERPAY"],
        "year": ["2024-03", "2024-03"],
        "dividend_payout": [50.0, 250.0],
    })
    validator = DataValidator({"profitandloss": df_pl})
    validator._check_dq12_dividend_cap()
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "OVERPAY"


def test_dq13_url_validity():
    """DQ-13: URL Validity."""
    df_co = pd.DataFrame({
        "id": ["TCS", "BADURL"],
        "website": ["https://www.tcs.com", "not_a_valid_url"],
    })
    validator = DataValidator({"companies": df_co})
    validator._check_dq13_url_validity()
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "BADURL"


def test_dq14_eps_sign():
    """DQ-14: EPS Sign Consistency."""
    df_pl = pd.DataFrame({
        "company_id": ["TCS", "MISMATCH"],
        "year": ["2024-03", "2024-03"],
        "net_profit": [1000.0, -500.0],
        "eps": [50.0, 20.0],  # Negative profit but positive EPS
    })
    validator = DataValidator({"profitandloss": df_pl})
    validator._check_dq14_eps_sign()
    assert len(validator.failures) == 1
    assert validator.failures[0]["company_id"] == "MISMATCH"
