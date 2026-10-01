"""Unit tests for Cash Flow KPIs & Capital Allocation Classifier (Day 11)."""

from src.analytics.cashflow_kpis import (
    PATTERN_CASH_ACCUMULATOR,
    PATTERN_DISTRESS_SIGNAL,
    PATTERN_GROWTH_FUNDED_DEBT,
    PATTERN_GROWTH_MIXED,
    PATTERN_LIQUIDATING_ASSETS,
    PATTERN_PRE_REVENUE_BURN,
    PATTERN_REINVESTOR,
    PATTERN_RESTRUCTURING,
    PATTERN_SHAREHOLDER_RETURNS,
    calculate_capex_intensity,
    calculate_cfo_quality_score,
    calculate_fcf_conversion,
    calculate_free_cash_flow,
    classify_capital_allocation,
)


def test_fcf_normal():
    """Test standard Free Cash Flow calculation: CFO + CFI."""
    assert calculate_free_cash_flow(150.0, -50.0) == 100.0


def test_fcf_negative_allowed():
    """Test Free Cash Flow when negative (capex exceeds CFO)."""
    assert calculate_free_cash_flow(30.0, -100.0) == -70.0


def test_fcf_none_handling():
    """Test Free Cash Flow returns None if any component is None."""
    assert calculate_free_cash_flow(None, -50.0) is None
    assert calculate_free_cash_flow(150.0, None) is None


def test_capex_intensity_asset_light():
    """Test CapEx Intensity < 3% classified as Asset Light."""
    val, label = calculate_capex_intensity(-2.0, 100.0)
    assert val == 2.0
    assert label == "Asset Light"


def test_capex_intensity_moderate():
    """Test CapEx Intensity 3-8% classified as Moderate."""
    val, label = calculate_capex_intensity(-5.5, 100.0)
    assert val == 5.5
    assert label == "Moderate"


def test_capex_intensity_capital_intensive():
    """Test CapEx Intensity > 8% classified as Capital Intensive."""
    val, label = calculate_capex_intensity(-12.0, 100.0)
    assert val == 12.0
    assert label == "Capital Intensive"


def test_fcf_conversion():
    """Test FCF conversion rate and tiers."""
    val, tier = calculate_fcf_conversion(70.0, 100.0)
    assert val == 70.0
    assert tier == "Efficient"

    val_heavy, tier_heavy = calculate_fcf_conversion(20.0, 100.0)
    assert val_heavy == 20.0
    assert tier_heavy == "CapEx Heavy"


def test_cfo_quality_score():
    """Test 5-year CFO quality score: avg of CFO/PAT."""
    cfo_series = [120.0, 110.0, 130.0, 140.0, 150.0]
    pat_series = [100.0, 100.0, 100.0, 100.0, 100.0]
    score, label = calculate_cfo_quality_score(cfo_series, pat_series)
    assert score == 1.3
    assert label == "High Quality Earnings"


def test_capital_allocation_patterns():
    """Test all 8 lifecycle patterns for Capital Allocation."""
    # Pattern 1a: (+, -, -) CFO/PAT <= 1 -> Reinvestor
    _, _, _, p1a = classify_capital_allocation(100.0, -60.0, -30.0, cfo_to_pat=0.8)
    assert p1a == PATTERN_REINVESTOR

    # Pattern 1b: (+, -, -) CFO/PAT > 1 -> Shareholder Returns
    _, _, _, p1b = classify_capital_allocation(150.0, -40.0, -80.0, cfo_to_pat=1.5)
    assert p1b == PATTERN_SHAREHOLDER_RETURNS

    # Pattern 2: (+, +, -) -> Liquidating Assets
    _, _, _, p2 = classify_capital_allocation(100.0, 50.0, -80.0)
    assert p2 == PATTERN_LIQUIDATING_ASSETS

    # Pattern 3: (-, +, +) -> Distress Signal
    _, _, _, p3 = classify_capital_allocation(-50.0, 20.0, 80.0)
    assert p3 == PATTERN_DISTRESS_SIGNAL

    # Pattern 4: (-, -, +) -> Growth Funded by Debt
    _, _, _, p4 = classify_capital_allocation(-50.0, -100.0, 180.0)
    assert p4 == PATTERN_GROWTH_FUNDED_DEBT

    # Pattern 5: (+, +, +) -> Cash Accumulator
    _, _, _, p5 = classify_capital_allocation(100.0, 50.0, 50.0)
    assert p5 == PATTERN_CASH_ACCUMULATOR

    # Pattern 6: (-, -, -) -> Pre-Revenue / Cash Burn
    _, _, _, p6 = classify_capital_allocation(-50.0, -50.0, -50.0)
    assert p6 == PATTERN_PRE_REVENUE_BURN

    # Pattern 7: (+, -, +) -> Growth / Mixed
    _, _, _, p7 = classify_capital_allocation(100.0, -80.0, 50.0)
    assert p7 == PATTERN_GROWTH_MIXED

    # Pattern 8: (-, +, -) -> Restructuring
    _, _, _, p8 = classify_capital_allocation(-30.0, 40.0, -20.0)
    assert p8 == PATTERN_RESTRUCTURING
