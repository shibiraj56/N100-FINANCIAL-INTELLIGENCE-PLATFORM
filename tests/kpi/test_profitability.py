"""Unit tests for Profitability KPIs (Day 08)."""

import logging
from src.analytics.ratios import (
    calculate_ebit_margin,
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    calculate_return_on_assets,
    calculate_return_on_capital_employed,
    calculate_return_on_equity,
)


def test_npm_normal():
    """Test standard Net Profit Margin calculation."""
    assert calculate_net_profit_margin(20.0, 100.0) == 20.0


def test_npm_zero_sales():
    """Test Net Profit Margin when sales is zero returns None."""
    assert calculate_net_profit_margin(20.0, 0.0) is None
    assert calculate_net_profit_margin(20.0, None) is None


def test_npm_negative_profit():
    """Test Net Profit Margin with loss is negative percentage."""
    assert calculate_net_profit_margin(-15.0, 100.0) == -15.0


def test_opm_normal():
    """Test standard Operating Profit Margin calculation."""
    assert calculate_operating_profit_margin(15.0, 100.0) == 15.0


def test_opm_divergence_logged(caplog):
    """Test OPM divergence > 1% emits a logger warning."""
    with caplog.at_level(logging.WARNING):
        val = calculate_operating_profit_margin(
            operating_profit=20.0,
            sales=100.0,
            source_opm=15.0,
            company_id="TEST",
            year="2024-03",
        )
        assert val == 20.0
        assert "OPM divergence for TEST (2024-03)" in caplog.text


def test_roe_positive():
    """Test ROE with positive equity returns expected percentage."""
    # net_profit = 100, equity = 100, reserves = 400 => total equity = 500 => ROE = 20.0%
    assert calculate_return_on_equity(100.0, 100.0, 400.0) == 20.0


def test_roe_neg_equity():
    """Test ROE with negative equity returns None."""
    assert calculate_return_on_equity(100.0, 50.0, -100.0) is None
    assert calculate_return_on_equity(100.0, 0.0, 0.0) is None


def test_roce_normal():
    """Test standard ROCE calculation: EBIT / Capital Employed."""
    # EBIT = 120 - 20 = 100, CE = 100 + 200 + 200 = 500 => ROCE = 20.0%
    assert (
        calculate_return_on_capital_employed(
            operating_profit=120.0,
            depreciation=20.0,
            equity_capital=100.0,
            reserves=200.0,
            borrowings=200.0,
        )
        == 20.0
    )


def test_roce_zero_capital():
    """Test ROCE returns None when capital employed <= 0."""
    assert (
        calculate_return_on_capital_employed(
            operating_profit=50.0,
            depreciation=10.0,
            equity_capital=-100.0,
            reserves=20.0,
            borrowings=50.0,
        )
        is None
    )


def test_roa_normal():
    """Test ROA calculation: net_profit / total_assets * 100."""
    assert calculate_return_on_assets(50.0, 1000.0) == 5.0


def test_roa_zero_assets():
    """Test ROA returns None when total_assets <= 0."""
    assert calculate_return_on_assets(50.0, 0.0) is None
    assert calculate_return_on_assets(50.0, -500.0) is None


def test_ebit_margin():
    """Test EBIT margin calculation."""
    assert calculate_ebit_margin(25.0, 5.0, 100.0) == 20.0
