"""Multi-Criteria Screener Router (Epic 11, Day 40)."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
import pandas as pd

from src.screener.engine import ScreenerEngine

router = APIRouter(prefix="/screener", tags=["Screener"])

_engine: Optional[ScreenerEngine] = None


def get_screener_engine() -> ScreenerEngine:
    """Lazy initialize ScreenerEngine singleton."""
    global _engine
    if _engine is None:
        _engine = ScreenerEngine()
    return _engine


@router.get("")
def run_screener(
    min_roe: Optional[float] = Query(None, description="Minimum Return on Equity (%)"),
    max_de: Optional[float] = Query(None, description="Maximum Debt-to-Equity ratio"),
    min_fcf: Optional[float] = Query(None, description="Minimum Free Cash Flow (₹ Cr)"),
    sector: Optional[str] = Query(None, description="Filter by broad sector name"),
    min_rev_cagr_5yr: Optional[float] = Query(None, description="Minimum 5-Year Revenue CAGR (%)"),
    min_pat_cagr_5yr: Optional[float] = Query(None, description="Minimum 5-Year PAT CAGR (%)"),
    max_pe: Optional[float] = Query(None, description="Maximum Price-to-Earnings ratio"),
) -> List[Dict[str, Any]]:
    """Run multi-criteria stock screening and return ranked companies with all metrics."""
    # Validation
    if min_roe is not None and (math.isnan(min_roe) or min_roe < -1000):
        raise HTTPException(status_code=400, detail="Invalid min_roe parameter.")
    if max_de is not None and (math.isnan(max_de) or max_de < 0):
        raise HTTPException(status_code=400, detail="Invalid max_de parameter (must be non-negative).")
    if max_pe is not None and (math.isnan(max_pe) or max_pe <= 0):
        raise HTTPException(status_code=400, detail="Invalid max_pe parameter (must be positive).")
    if min_rev_cagr_5yr is not None and math.isnan(min_rev_cagr_5yr):
        raise HTTPException(status_code=400, detail="Invalid min_rev_cagr_5yr parameter.")
    if min_pat_cagr_5yr is not None and math.isnan(min_pat_cagr_5yr):
        raise HTTPException(status_code=400, detail="Invalid min_pat_cagr_5yr parameter.")

    engine = get_screener_engine()
    df_universe = engine.fetch_universe()

    filter_criteria: Dict[str, Any] = {}
    if min_roe is not None:
        filter_criteria["roe_min"] = min_roe
    if max_de is not None:
        filter_criteria["de_max"] = max_de
    if min_fcf is not None:
        filter_criteria["fcf_min"] = min_fcf
    if min_rev_cagr_5yr is not None:
        filter_criteria["rev_cagr_5yr_min"] = min_rev_cagr_5yr
    if min_pat_cagr_5yr is not None:
        filter_criteria["pat_cagr_5yr_min"] = min_pat_cagr_5yr
    if max_pe is not None:
        filter_criteria["pe_max"] = max_pe

    filtered = engine.apply_filters(df_universe, filter_criteria)

    if sector and sector.strip():
        sec_clean = sector.strip().lower()
        filtered = filtered[filtered["broad_sector"].astype(str).str.lower() == sec_clean]

    # Rank and sort
    sorted_df = engine.rank_and_sort(filtered)
    # Replace NaN/inf with None for valid JSON serialization
    sorted_df = sorted_df.replace({float("nan"): None, float("inf"): None, float("-inf"): None})
    return sorted_df.to_dict(orient="records")
