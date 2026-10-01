"""Unit tests for Dashboard Cached Database Loader (Epic 05, Day 27)."""

import pandas as pd
import pytest

from src.dashboard.utils.db import (
    get_companies,
    get_sectors,
    get_ratios,
    get_pl,
    get_bs,
    get_cf,
    get_peers,
    get_peer_percentiles,
    get_valuation,
    get_home_kpis,
    get_capital_allocation,
    get_annual_reports,
    get_prosandcons,
)


def test_get_companies():
    """Verify get_companies returns all 92 companies."""
    df = get_companies()
    assert len(df) == 92
    assert "ticker" in df.columns
    assert "company_name" in df.columns
    assert "broad_sector" in df.columns


def test_get_sectors():
    """Verify get_sectors returns non-empty breakdown."""
    df = get_sectors()
    assert not df.empty
    assert "broad_sector" in df.columns
    assert "company_count" in df.columns


def test_get_ratios():
    """Verify get_ratios returns valid ratio histories and handles missing ticker."""
    df_tcs = get_ratios("TCS")
    assert not df_tcs.empty
    assert len(df_tcs) >= 10
    assert "return_on_equity_pct" in df_tcs.columns

    # Specific year
    df_tcs_2024 = get_ratios("TCS", year="2024-03")
    assert len(df_tcs_2024) == 1

    # Missing ticker
    df_empty = get_ratios("NON_EXISTENT_TICKER")
    assert df_empty.empty


def test_get_pl():
    """Verify get_pl returns P&L statements."""
    df_pl = get_pl("INFY")
    assert not df_pl.empty
    assert "sales" in df_pl.columns
    assert "net_profit" in df_pl.columns


def test_get_bs():
    """Verify get_bs returns Balance Sheet statements."""
    df_bs = get_bs("RELIANCE")
    assert not df_bs.empty
    assert "total_assets" in df_bs.columns


def test_get_cf():
    """Verify get_cf returns Cash Flow statements."""
    df_cf = get_cf("HDFCBANK")
    assert not df_cf.empty
    assert "operating_activity" in df_cf.columns


def test_get_peers():
    """Verify get_peers returns all 11 peer groups and specific group."""
    df_all = get_peers()
    assert not df_all.empty
    assert df_all["peer_group_name"].nunique() == 11

    df_it = get_peers("IT Services")
    assert not df_it.empty
    assert (df_it["peer_group_name"] == "IT Services").all()


def test_get_valuation():
    """Verify get_valuation returns valid metrics and flags."""
    val_tcs = get_valuation("TCS")
    assert isinstance(val_tcs, dict)
    assert val_tcs["company_id"] == "TCS"
    assert val_tcs["pe_ratio"] is not None
    assert val_tcs["valuation_flag"] in ["Caution", "Discount", "Fair"]

    # Missing ticker
    val_missing = get_valuation("XYZ_UNKNOWN")
    assert val_missing["valuation_flag"] == "Fair"
    assert val_missing["pe_ratio"] is None


def test_get_home_kpis():
    """Verify get_home_kpis returns valid aggregate numbers."""
    kpis = get_home_kpis(year="2024-03")
    assert 90 <= kpis["total_companies"] <= 92
    assert kpis["avg_roe"] > 0
    assert kpis["median_pe"] > 0
    assert kpis["debt_free_count"] >= 5


def test_get_capital_allocation():
    """Verify get_capital_allocation returns corporate lifecycle patterns."""
    df_ca = get_capital_allocation()
    assert 90 <= len(df_ca) <= 92
    assert "pattern_label" in df_ca.columns


def test_get_annual_reports():
    """Verify get_annual_reports returns document URLs."""
    df_rep = get_annual_reports("TCS")
    assert not df_rep.empty
    assert "annual_report" in df_rep.columns


def test_get_prosandcons():
    """Verify get_prosandcons returns valid dict structure."""
    pac = get_prosandcons("TCS")
    assert "pros" in pac
    assert "cons" in pac
    assert isinstance(pac["pros"], list)
    assert isinstance(pac["cons"], list)
