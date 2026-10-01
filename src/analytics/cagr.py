"""CAGR Growth Engine.

Calculates multi-period (3-year, 5-year, 10-year) CAGR for financial metrics
(Revenue, PAT, EPS) and rigorously handles all 6 edge case conditions.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd

logger = logging.getLogger(__name__)

# CAGR Status Flags
FLAG_NORMAL = "NORMAL"
FLAG_DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
FLAG_TURNAROUND = "TURNAROUND"
FLAG_BOTH_NEGATIVE = "BOTH_NEGATIVE"
FLAG_ZERO_BASE = "ZERO_BASE"
FLAG_INSUFFICIENT = "INSUFFICIENT"


def calculate_cagr(
    start_val: Optional[float],
    end_val: Optional[float],
    n_years: int,
) -> Tuple[Optional[float], str, str]:
    """Calculate Compound Annual Growth Rate (CAGR) with comprehensive edge-case classification.

    Formula: ((end / start) ** (1 / n) - 1) * 100

    Decision Table:
    1. start > 0 and end > 0: Computed normally (NORMAL) -> e.g. "18.3%"
    2. start > 0 and end <= 0: None (DECLINE_TO_LOSS) -> "N/A — turned loss"
    3. start < 0 and end > 0: None (TURNAROUND) -> "Turnaround ↑"
    4. start <= 0 and end <= 0: None (BOTH_NEGATIVE) -> "N/A — both loss"
    5. start == 0: None (ZERO_BASE) -> "N/A — base=0"
    6. Insufficient history (< n years or None): None (INSUFFICIENT) -> "N/A — < 3yr"

    Returns:
        (cagr_percentage, flag_name, display_text)
    """
    if n_years <= 0 or start_val is None or end_val is None:
        return (None, FLAG_INSUFFICIENT, f"N/A — < {n_years}yr")

    # Case 5: Zero base
    if start_val == 0:
        return (None, FLAG_ZERO_BASE, "N/A — base=0")

    # Case 2: Positive start turned to loss/zero
    if start_val > 0 and end_val <= 0:
        return (None, FLAG_DECLINE_TO_LOSS, "N/A — turned loss")

    # Case 3: Negative start turned positive (Turnaround)
    if start_val < 0 and end_val > 0:
        return (None, FLAG_TURNAROUND, "Turnaround ↑")

    # Case 4: Both start and end negative / non-positive
    if start_val <= 0 and end_val <= 0:
        return (None, FLAG_BOTH_NEGATIVE, "N/A — both loss")

    # Case 1: Standard positive start and end
    try:
        ratio = end_val / start_val
        cagr = (pow(ratio, 1.0 / n_years) - 1.0) * 100.0
        cagr_rounded = round(cagr, 2)
        return (cagr_rounded, FLAG_NORMAL, f"{cagr_rounded:.1f}%")
    except Exception as e:
        logger.warning("Error calculating CAGR: %s", e)
        return (None, FLAG_INSUFFICIENT, "N/A — error")


def calculate_company_cagrs(
    records: List[Dict[str, Union[str, float, None]]],
    metric_key: str,
    periods: Tuple[int, ...] = (3, 5, 10),
) -> Dict[str, Dict[str, Tuple[Optional[float], str, str]]]:
    """Calculate multi-period CAGRs for a company across its annual records.

    Args:
        records: List of annual record dicts containing at least 'year' and metric_key.
        metric_key: The metric to compute CAGR for (e.g., 'sales', 'net_profit', 'eps').
        periods: Tuple of lookback windows (defaults to 3, 5, 10).

    Returns:
        Dict mapping year string -> {period_key: (cagr_val, flag, display_str)}
        e.g. {'2024-03': {'cagr_3yr': (12.5, 'NORMAL', '12.5%'), ...}}
    """
    # Sort records by parsed year
    valid_records = [
        r for r in records if r.get("year") and r.get(metric_key) is not None
    ]

    def parse_yr(y: str) -> int:
        part = str(y).split("-")[0]
        try:
            return int(part)
        except ValueError:
            return 0

    sorted_records = sorted(valid_records, key=lambda r: parse_yr(r["year"]))
    results: Dict[str, Dict[str, Tuple[Optional[float], str, str]]] = {}

    for i, curr_rec in enumerate(sorted_records):
        curr_year = str(curr_rec["year"])
        curr_val = float(curr_rec[metric_key])
        curr_yr_int = parse_yr(curr_year)
        results[curr_year] = {}

        for p in periods:
            cagr_key = f"cagr_{p}yr"
            # Look for record p years prior
            target_yr_int = curr_yr_int - p
            prior_rec = next(
                (r for r in sorted_records if parse_yr(r["year"]) == target_yr_int),
                None,
            )

            # Fallback to index-based if years are consecutive
            if prior_rec is None and i >= p:
                candidate = sorted_records[i - p]
                if parse_yr(candidate["year"]) == curr_yr_int - p:
                    prior_rec = candidate

            if prior_rec is None:
                results[curr_year][cagr_key] = (
                    None,
                    FLAG_INSUFFICIENT,
                    f"N/A — < {p}yr",
                )
            else:
                start_val = float(prior_rec[metric_key])
                results[curr_year][cagr_key] = calculate_cagr(start_val, curr_val, p)

    return results
