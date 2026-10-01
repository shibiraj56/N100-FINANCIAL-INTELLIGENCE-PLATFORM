"""Integration QA & Performance Benchmarks for Dashboard (Epic 05, Day 27)."""

import time
import pandas as pd
import pytest

from src.dashboard.utils.db import (
    get_companies,
    get_ratios,
    get_pl,
    get_bs,
    get_cf,
    get_valuation,
    get_prosandcons,
)
from src.screener.engine import ScreenerEngine


def test_company_profile_load_time_under_3_seconds():
    """Verify Company Profile data pipeline loads in < 3 seconds for 5 representative tickers."""
    test_tickers = ["TCS", "HDFCBANK", "RELIANCE", "ITC", "SUNPHARMA"]
    
    for ticker in test_tickers:
        start_time = time.perf_counter()
        
        # Simulate all queries invoked when rendering Company Profile screen
        ratios = get_ratios(ticker)
        pl = get_pl(ticker)
        bs = get_bs(ticker)
        cf = get_cf(ticker)
        val = get_valuation(ticker)
        pac = get_prosandcons(ticker)
        
        elapsed = time.perf_counter() - start_time
        assert elapsed < 3.0, f"Profile load for {ticker} took {elapsed:.2f}s (exceeded 3.0s threshold)"


def test_multi_sector_tickers_data_integrity():
    """Test data pipelines across 10 tickers from diverse sectors."""
    sample_tickers = [
        "TCS",         # IT
        "INFY",        # IT
        "HDFCBANK",    # Financials / Private Bank
        "SBIN",        # Financials / Public Bank
        "ITC",         # FMCG / Consumer Staples
        "HINDUNILVR",  # FMCG / Consumer Staples
        "RELIANCE",    # Energy / Oil & Gas
        "ONGC",        # Energy / Oil & Gas
        "SUNPHARMA",   # Healthcare / Pharma
        "TATAMOTORS",  # Consumer Discretionary / Auto
    ]
    for ticker in sample_tickers:
        df_r = get_ratios(ticker)
        assert not df_r.empty, f"Missing ratios for {ticker}"
        df_pl = get_pl(ticker)
        assert not df_pl.empty, f"Missing P&L for {ticker}"
        val = get_valuation(ticker)
        assert val["valuation_flag"] in ["Caution", "Discount", "Fair"]


def test_screener_extreme_values_no_crash():
    """Test screener filter engine with extreme minimum and maximum slider values."""
    engine = ScreenerEngine()
    df_uni = engine.get_universe_data(year="2024-03")
    
    # 1. All metrics at maximum stringency (impossible constraints) -> should return 0 rows cleanly without error
    impossible_filters = {
        "roe_min": 1000.0,
        "de_max": 0.0,
        "fcf_min": 1000000.0,
        "rev_cagr_5yr_min": 500.0,
        "pe_max": 0.01,
    }
    df_res_empty = engine.apply_filters(df_uni, impossible_filters)
    assert len(df_res_empty) == 0

    # 2. No filters -> should return all 92 companies
    df_res_all = engine.apply_filters(df_uni, {})
    assert len(df_res_all) == 92

    # 3. Very loose filters -> handles all positive metrics without crash
    loose_filters = {
        "roe_min": -100.0,
        "de_max": 100.0,
        "fcf_min": -1000000.0,
        "rev_cagr_5yr_min": -100.0,
    }
    df_res_loose = engine.apply_filters(df_uni, loose_filters)
    assert len(df_res_loose) >= 85
