"""Comprehensive Unit Tests for Financial Ratio & KPI Formulas (Epic 02 / Day 41).

Contains 20 focused unit tests covering profitability, leverage edge cases,
flags, CAGR anomalies, and cash flow quality indicators.
"""

import pytest
from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_return_on_equity,
    calculate_return_on_capital_employed,
    calculate_return_on_assets,
    calculate_debt_to_equity,
    is_high_leverage,
    calculate_interest_coverage,
    calculate_asset_turnover,
)
from src.analytics.cagr import calculate_cagr, FLAG_TURNAROUND, FLAG_DECLINE_TO_LOSS, FLAG_NORMAL
from src.analytics.cashflow_kpis import calculate_cfo_quality_score


# 1. ROE with positive equity
def test_01_roe_positive_equity():
    assert calculate_return_on_equity(100.0, 200.0, 300.0) == 20.0


# 2. ROE with negative equity (returns None)
def test_02_roe_negative_equity():
    assert calculate_return_on_equity(50.0, 10.0, -50.0) is None


# 3. ROE with zero equity (returns None)
def test_03_roe_zero_equity():
    assert calculate_return_on_equity(50.0, 0.0, 0.0) is None


# 4. D/E for debt-free company (returns 0.0, not None)
def test_04_de_debt_free():
    assert calculate_debt_to_equity(0.0, 100.0, 400.0) == 0.0


# 5. D/E normal positive
def test_05_de_normal_positive():
    assert calculate_debt_to_equity(250.0, 100.0, 400.0) == 0.5


# 6. D/E with negative equity (returns None)
def test_06_de_negative_equity():
    assert calculate_debt_to_equity(200.0, 50.0, -100.0) is None


# 7. D/E > 5 flag for non-financial company (returns True)
def test_07_high_leverage_flag_non_financial():
    assert is_high_leverage(5.5, broad_sector="Industrials") is True


# 8. D/E > 5 flag for Financials company (returns False - bank carve-out)
def test_08_high_leverage_flag_financial_carveout():
    assert is_high_leverage(7.5, broad_sector="Financials") is False


# 9. ICR normal calculation
def test_09_icr_normal():
    icr, label, warning = calculate_interest_coverage(150.0, 0.0, 30.0)
    assert icr == 5.0
    assert warning is False


# 10. ICR when interest = 0 (returns None, 'Debt Free')
def test_10_icr_zero_interest():
    icr, label, warning = calculate_interest_coverage(100.0, 0.0, 0.0)
    assert icr is None
    assert label == "Debt Free"
    assert warning is False


# 11. ICR warning flag (< 1.5)
def test_11_icr_warning_flag():
    icr, label, warning = calculate_interest_coverage(120.0, 0.0, 100.0)
    assert icr == 1.2
    assert warning is True


# 12. OPM normal calculation
def test_12_opm_normal():
    assert calculate_operating_profit_margin(250.0, 1000.0) == 25.0


# 13. OPM zero sales (returns None)
def test_13_opm_zero_sales():
    assert calculate_operating_profit_margin(50.0, 0.0) is None


# 14. NPM normal and zero sales
def test_14_npm_calculation():
    assert calculate_net_profit_margin(120.0, 1000.0) == 12.0
    assert calculate_net_profit_margin(50.0, 0.0) is None


# 15. ROCE normal calculation
def test_15_roce_normal():
    # EBIT=200, Equity=100, Reserves=400, Borrowings=500 -> CapEmployed=1000 -> 20.0%
    assert calculate_return_on_capital_employed(200.0, 100.0, 400.0, 500.0) == 20.0


# 16. ROA normal calculation
def test_16_roa_normal():
    assert calculate_return_on_assets(150.0, 1500.0) == 10.0
    assert calculate_return_on_assets(150.0, 0.0) is None


# 17. CAGR normal calculation
def test_17_cagr_normal():
    val, flag, _ = calculate_cagr(100.0, 200.0, 5)
    assert flag == FLAG_NORMAL
    assert val == 14.87


# 18. CAGR turnaround flag (negative base to positive end)
def test_18_cagr_turnaround_flag():
    val, flag, _ = calculate_cagr(-50.0, 120.0, 5)
    assert flag == FLAG_TURNAROUND
    assert val is None


# 19. CAGR decline-to-loss (positive base to negative end)
def test_19_cagr_decline_to_loss():
    val, flag, _ = calculate_cagr(100.0, -20.0, 5)
    assert flag == FLAG_DECLINE_TO_LOSS
    assert val is None


# 20. CFO Quality score calculation (High Quality vs Accrual Risk)
def test_20_cfo_quality_score():
    score_hq, label_hq = calculate_cfo_quality_score([120, 130, 140, 150, 160], [100, 100, 100, 100, 100])
    assert "High Quality" in label_hq
    score_ar, label_ar = calculate_cfo_quality_score([20, 30, 40, 50, 60], [100, 100, 100, 100, 100])
    assert label_ar == "Accrual Risk"
