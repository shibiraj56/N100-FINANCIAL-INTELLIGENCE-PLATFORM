"""Unit tests for CAGR Growth Engine covering all 6 edge cases (Day 10)."""

import pytest
from src.analytics.cagr import (
    FLAG_BOTH_NEGATIVE,
    FLAG_DECLINE_TO_LOSS,
    FLAG_INSUFFICIENT,
    FLAG_NORMAL,
    FLAG_TURNAROUND,
    FLAG_ZERO_BASE,
    calculate_cagr,
    calculate_company_cagrs,
)


def test_cagr_normal_5yr():
    """Case 1: Standard 5-year CAGR with positive start and end."""
    cagr, flag, display = calculate_cagr(100.0, 161.051, 5)
    assert flag == FLAG_NORMAL
    assert round(cagr, 1) == 10.0
    assert "10.0%" in display


def test_cagr_normal_3yr():
    """Case 1: Standard 3-year CAGR."""
    cagr, flag, display = calculate_cagr(100.0, 133.1, 3)
    assert flag == FLAG_NORMAL
    assert round(cagr, 1) == 10.0


def test_cagr_normal_10yr():
    """Case 1: Standard 10-year CAGR."""
    cagr, flag, display = calculate_cagr(100.0, 259.37, 10)
    assert flag == FLAG_NORMAL
    assert round(cagr, 1) == 10.0


def test_cagr_decline_to_loss():
    """Case 2: Positive base turned negative (loss)."""
    cagr, flag, display = calculate_cagr(100.0, -25.0, 3)
    assert cagr is None
    assert flag == FLAG_DECLINE_TO_LOSS
    assert display == "N/A — turned loss"


def test_cagr_decline_to_zero():
    """Case 2: Positive base turned zero."""
    cagr, flag, display = calculate_cagr(100.0, 0.0, 3)
    assert cagr is None
    assert flag == FLAG_DECLINE_TO_LOSS
    assert display == "N/A — turned loss"


def test_cagr_turnaround():
    """Case 3: Negative base turned positive (Turnaround)."""
    cagr, flag, display = calculate_cagr(-100.0, 200.0, 3)
    assert cagr is None
    assert flag == FLAG_TURNAROUND
    assert display == "Turnaround ↑"


def test_cagr_both_negative():
    """Case 4: Both start and end negative."""
    cagr, flag, display = calculate_cagr(-100.0, -50.0, 3)
    assert cagr is None
    assert flag == FLAG_BOTH_NEGATIVE
    assert display == "N/A — both loss"


def test_cagr_zero_base():
    """Case 5: Zero base value."""
    cagr, flag, display = calculate_cagr(0.0, 150.0, 3)
    assert cagr is None
    assert flag == FLAG_ZERO_BASE
    assert display == "N/A — base=0"


def test_cagr_insufficient_history():
    """Case 6: Insufficient history or None values."""
    cagr, flag, display = calculate_cagr(None, 150.0, 3)
    assert cagr is None
    assert flag == FLAG_INSUFFICIENT

    cagr, flag, display = calculate_cagr(100.0, 150.0, 0)
    assert cagr is None
    assert flag == FLAG_INSUFFICIENT


def test_calculate_company_cagrs():
    """Test multi-period CAGR across chronological company records."""
    records = [
        {"year": "2019-03", "sales": 100.0},
        {"year": "2020-03", "sales": 110.0},
        {"year": "2021-03", "sales": 120.0},
        {"year": "2022-03", "sales": 133.1},  # 3yr from 2019: 10%
        {"year": "2023-03", "sales": 145.0},
        {"year": "2024-03", "sales": 161.05},  # 5yr from 2019: 10%
    ]
    results = calculate_company_cagrs(records, "sales", periods=(3, 5))

    # Check 2022 3yr CAGR
    cagr_3yr, flag_3yr, _ = results["2022-03"]["cagr_3yr"]
    assert flag_3yr == FLAG_NORMAL
    assert round(cagr_3yr, 1) == 10.0

    # Check 2024 5yr CAGR
    cagr_5yr, flag_5yr, _ = results["2024-03"]["cagr_5yr"]
    assert flag_5yr == FLAG_NORMAL
    assert round(cagr_5yr, 1) == 10.0

    # Check 2019 (no lookback)
    _, flag_no_hist, _ = results["2019-03"]["cagr_3yr"]
    assert flag_no_hist == FLAG_INSUFFICIENT
