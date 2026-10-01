"""Unit tests for Leverage and Efficiency KPIs (Day 09)."""

from src.analytics.ratios import (
    calculate_asset_turnover,
    calculate_debt_to_equity,
    calculate_interest_coverage,
    calculate_net_debt,
    is_high_leverage,
)


def test_de_normal():
    """Test standard Debt-to-Equity calculation."""
    # borrowings = 250, equity = 100, reserves = 400 => total equity = 500 => D/E = 0.5
    assert calculate_debt_to_equity(250.0, 100.0, 400.0) == 0.5


def test_de_debtfree():
    """Test Debt-to-Equity for debt-free company returns 0.0."""
    assert calculate_debt_to_equity(0.0, 100.0, 400.0) == 0.0
    assert calculate_debt_to_equity(None, 100.0, 400.0) == 0.0


def test_de_negative_equity():
    """Test Debt-to-Equity returns None when equity is negative."""
    assert calculate_debt_to_equity(200.0, 50.0, -100.0) is None


def test_high_leverage_flag_non_financial():
    """Test high leverage flag (>5.0) triggers for non-financial companies."""
    assert is_high_leverage(6.0, broad_sector="Consumer") is True
    assert is_high_leverage(3.0, broad_sector="Consumer") is False


def test_high_leverage_flag_financial_carveout():
    """Test bank carve-out: high leverage flag is suppressed for Financials sector."""
    assert is_high_leverage(8.5, broad_sector="Financials") is False
    assert is_high_leverage(12.0, broad_sector="financials") is False


def test_icr_normal():
    """Test standard Interest Coverage Ratio: (op_profit + other_income) / interest."""
    icr, label, warning = calculate_interest_coverage(
        operating_profit=180.0, other_income=20.0, interest=50.0
    )
    assert icr == 4.0
    assert label == "4.00x"
    assert warning is False


def test_icr_warning_flag():
    """Test ICR < 1.5 triggers warning flag."""
    icr, label, warning = calculate_interest_coverage(
        operating_profit=100.0, other_income=20.0, interest=100.0
    )
    assert icr == 1.2
    assert label == "1.20x"
    assert warning is True


def test_icr_debtfree():
    """Test ICR returns None and 'Debt Free' label when interest is 0."""
    icr, label, warning = calculate_interest_coverage(
        operating_profit=100.0, other_income=20.0, interest=0.0
    )
    assert icr is None
    assert label == "Debt Free"
    assert warning is False


def test_net_debt():
    """Test Net Debt: borrowings - investments."""
    assert calculate_net_debt(500.0, 200.0) == 300.0
    assert calculate_net_debt(0.0, 200.0) == -200.0


def test_asset_turnover():
    """Test Asset Turnover ratio: sales / total_assets."""
    assert calculate_asset_turnover(2000.0, 1000.0) == 2.0
    assert calculate_asset_turnover(2000.0, 0.0) is None
