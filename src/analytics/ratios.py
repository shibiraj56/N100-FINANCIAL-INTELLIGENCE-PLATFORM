"""Financial Ratio Engine - Profitability, Leverage, and Efficiency Ratios.

Implements core ratio calculations, edge case handling (negative equity, debt-free,
bank carve-outs, division by zero), and warning flags.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def calculate_net_profit_margin(
    net_profit: Optional[float], sales: Optional[float]
) -> Optional[float]:
    """Calculate Net Profit Margin percentage: net_profit / sales * 100.
    
    Returns None if sales <= 0 or if values are missing.
    """
    if sales is None or net_profit is None or sales <= 0:
        return None
    return round((net_profit / sales) * 100, 2)


def calculate_operating_profit_margin(
    operating_profit: Optional[float],
    sales: Optional[float],
    source_opm: Optional[float] = None,
    company_id: str = "",
    year: str = "",
) -> Optional[float]:
    """Calculate Operating Profit Margin percentage: operating_profit / sales * 100.
    
    Cross-checks against source opm_percentage if provided and logs if difference > 1%.
    Returns None if sales <= 0 or values are missing.
    """
    if sales is None or operating_profit is None or sales <= 0:
        return None
    computed_opm = round((operating_profit / sales) * 100, 2)
    if source_opm is not None:
        diff = abs(computed_opm - source_opm)
        if diff > 1.0:
            logger.warning(
                "OPM divergence for %s (%s): computed=%.2f%%, source=%.2f%% (diff=%.2f%%)",
                company_id,
                year,
                computed_opm,
                source_opm,
                diff,
            )
    return computed_opm


def calculate_ebit_margin(
    operating_profit: Optional[float],
    depreciation: Optional[float],
    sales: Optional[float],
) -> Optional[float]:
    """Calculate EBIT Margin percentage: (operating_profit - depreciation) / sales * 100."""
    if sales is None or sales <= 0 or operating_profit is None:
        return None
    ebit = operating_profit - (depreciation or 0.0)
    return round((ebit / sales) * 100, 2)


def calculate_return_on_equity(
    net_profit: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float],
) -> Optional[float]:
    """Calculate Return on Equity (ROE) percentage: net_profit / (equity + reserves) * 100.
    
    Returns None if equity + reserves <= 0 or values are missing.
    """
    if net_profit is None:
        return None
    if equity_capital is None and reserves is None:
        return None
    total_equity = (equity_capital or 0.0) + (reserves or 0.0)
    if total_equity <= 0:
        logger.info("ROE is None due to non-positive equity: %.2f", total_equity)
        return None
    return round((net_profit / total_equity) * 100, 2)


def calculate_return_on_capital_employed(
    operating_profit: Optional[float],
    depreciation: Optional[float] = 0.0,
    equity_capital: Optional[float] = None,
    reserves: Optional[float] = None,
    borrowings: Optional[float] = None,
    is_financial: bool = False,
) -> Optional[float]:
    """Calculate Return on Capital Employed (ROCE) percentage.
    
    ROCE = EBIT / (equity + reserves + borrowings) * 100
    where EBIT = operating_profit - depreciation (or EBIT directly if 4 arguments passed).
    For Financials broad_sector, benchmark is sector-relative.
    Returns None if capital employed <= 0 or values missing.
    """
    if operating_profit is None:
        return None
    # Support 4-argument call signature: calculate_return_on_capital_employed(ebit, equity, reserves, borrowings)
    if borrowings is None and equity_capital is not None and reserves is not None:
        ebit = operating_profit
        eq = depreciation or 0.0
        res = equity_capital or 0.0
        borr = reserves or 0.0
        capital_employed = eq + res + borr
        if capital_employed <= 0:
            return None
        return round((ebit / capital_employed) * 100, 2)

    if equity_capital is None and reserves is None and borrowings is None:
        return None
    ebit = operating_profit - (depreciation or 0.0)
    capital_employed = (
        (equity_capital or 0.0) + (reserves or 0.0) + (borrowings or 0.0)
    )
    if capital_employed <= 0:
        return None
    return round((ebit / capital_employed) * 100, 2)


def calculate_return_on_assets(
    net_profit: Optional[float], total_assets: Optional[float]
) -> Optional[float]:
    """Calculate Return on Assets (ROA) percentage: net_profit / total_assets * 100.
    
    Returns None if total_assets <= 0 or values are missing.
    """
    if total_assets is None or net_profit is None or total_assets <= 0:
        return None
    return round((net_profit / total_assets) * 100, 2)


def calculate_debt_to_equity(
    borrowings: Optional[float],
    equity_capital: Optional[float],
    reserves: Optional[float],
) -> Optional[float]:
    """Calculate Debt-to-Equity ratio: borrowings / (equity + reserves).
    
    Returns 0.0 for debt-free companies (borrowings == 0).
    Returns None if equity + reserves <= 0 (negative/zero equity).
    """
    if equity_capital is None and reserves is None:
        return None
    total_equity = (equity_capital or 0.0) + (reserves or 0.0)
    if total_equity <= 0:
        return None
    b = borrowings or 0.0
    if b == 0.0:
        return 0.0
    return round(b / total_equity, 2)


def is_high_leverage(
    debt_to_equity: Optional[float], broad_sector: Optional[str] = None
) -> bool:
    """Check if company has high leverage (D/E > 5.0).
    
    Bank Carve-out: High leverage is structurally normal for Financials sector,
    so the flag is suppressed (returns False) for broad_sector == 'Financials'.
    """
    if broad_sector and broad_sector.strip().lower() == "financials":
        return False
    if debt_to_equity is not None and debt_to_equity > 5.0:
        return True
    return False


def calculate_interest_coverage(
    operating_profit: Optional[float],
    other_income: Optional[float],
    interest: Optional[float],
) -> Tuple[Optional[float], str, bool]:
    """Calculate Interest Coverage Ratio (ICR): (operating_profit + other_income) / interest.
    
    Returns:
        tuple of (icr_value, display_label, icr_warning_flag)
        - If interest == 0 or negative: (None, 'Debt Free', False)
        - If ICR < 1.5: icr_warning_flag is True
    """
    if operating_profit is None and other_income is None:
        return (None, "N/A", False)
    earnings = (operating_profit or 0.0) + (other_income or 0.0)
    if interest is None or interest <= 0:
        return (None, "Debt Free", False)
    icr = round(earnings / interest, 2)
    warning = icr < 1.5
    label = f"{icr:.2f}x"
    return (icr, label, warning)


def calculate_net_debt(
    borrowings: Optional[float], investments: Optional[float]
) -> Optional[float]:
    """Calculate Net Debt: borrowings - investments (liquid proxy)."""
    if borrowings is None and investments is None:
        return None
    return round((borrowings or 0.0) - (investments or 0.0), 2)


def calculate_asset_turnover(
    sales: Optional[float], total_assets: Optional[float]
) -> Optional[float]:
    """Calculate Asset Turnover ratio: sales / total_assets.
    
    Returns None if total_assets <= 0 or values are missing.
    """
    if total_assets is None or sales is None or total_assets <= 0:
        return None
    return round(sales / total_assets, 4)
