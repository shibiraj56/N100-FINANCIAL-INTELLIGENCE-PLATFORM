"""Shared Cached Data Loader for Streamlit Dashboard (Epic 05, Day 22).

All database query functions are wrapped with @st.cache_data(ttl=600)
to guarantee high-performance UI rendering and sub-second navigation.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(root_dir, "data", "nifty100.db")
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(root_dir, "nifty100.db")


def get_db_connection() -> sqlite3.Connection:
    """Create a read-only SQLite database connection."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """Fetch all 92 companies with metadata, sectors, and latest stats."""
    conn = get_db_connection()
    query = """
    SELECT 
        c.id AS ticker,
        c.company_name,
        c.company_logo,
        c.about_company,
        c.website,
        c.nse_profile,
        c.bse_profile,
        c.face_value,
        c.book_value,
        COALESCE(s.broad_sector, 'Unknown') AS broad_sector,
        COALESCE(s.sub_sector, 'Unknown') AS sub_sector,
        s.index_weight_pct,
        s.market_cap_category
    FROM companies c
    LEFT JOIN sectors s ON c.id = s.company_id
    ORDER BY c.company_name ASC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """Fetch sector breakdown with company counts and index weights."""
    conn = get_db_connection()
    query = """
    SELECT 
        COALESCE(s.broad_sector, 'Unknown') AS broad_sector,
        COALESCE(s.sub_sector, 'Unknown') AS sub_sector,
        COUNT(DISTINCT s.company_id) AS company_count,
        ROUND(SUM(COALESCE(s.index_weight_pct, 0)), 2) AS total_weight_pct
    FROM sectors s
    GROUP BY s.broad_sector, s.sub_sector
    ORDER BY company_count DESC
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_ratios(ticker: str, year: Optional[str] = None) -> pd.DataFrame:
    """Fetch financial ratios for a given company ticker across all or specific years."""
    conn = get_db_connection()
    if year:
        query = "SELECT * FROM financial_ratios WHERE company_id = ? AND year = ? ORDER BY year ASC"
        df = pd.read_sql(query, conn, params=(ticker.upper(), year))
    else:
        query = "SELECT * FROM financial_ratios WHERE company_id = ? ORDER BY year ASC"
        df = pd.read_sql(query, conn, params=(ticker.upper(),))
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    """Fetch 10-year Profit & Loss statements for a company."""
    conn = get_db_connection()
    query = "SELECT * FROM profitandloss WHERE company_id = ? ORDER BY year ASC"
    df = pd.read_sql(query, conn, params=(ticker.upper(),))
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    """Fetch 10-year Balance Sheet statements for a company."""
    conn = get_db_connection()
    query = "SELECT * FROM balancesheet WHERE company_id = ? ORDER BY year ASC"
    df = pd.read_sql(query, conn, params=(ticker.upper(),))
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    """Fetch 10-year Cash Flow statements for a company."""
    conn = get_db_connection()
    query = "SELECT * FROM cashflow WHERE company_id = ? ORDER BY year ASC"
    df = pd.read_sql(query, conn, params=(ticker.upper(),))
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_peers(group_name: Optional[str] = None) -> pd.DataFrame:
    """Fetch peer groups and their constituent companies."""
    conn = get_db_connection()
    if group_name:
        query = """
        SELECT pg.peer_group_name, pg.company_id, pg.is_benchmark, c.company_name, s.broad_sector
        FROM peer_groups pg
        JOIN companies c ON pg.company_id = c.id
        LEFT JOIN sectors s ON pg.company_id = s.company_id
        WHERE pg.peer_group_name = ?
        ORDER BY pg.is_benchmark DESC, c.company_name ASC
        """
        df = pd.read_sql(query, conn, params=(group_name,))
    else:
        query = """
        SELECT pg.peer_group_name, pg.company_id, pg.is_benchmark, c.company_name, s.broad_sector
        FROM peer_groups pg
        JOIN companies c ON pg.company_id = c.id
        LEFT JOIN sectors s ON pg.company_id = s.company_id
        ORDER BY pg.peer_group_name ASC, pg.is_benchmark DESC, c.company_name ASC
        """
        df = pd.read_sql(query, conn)
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_peer_percentiles(peer_group_name: str, year: str = "2024-03") -> pd.DataFrame:
    """Fetch intra-group percentile rankings for all metrics in a peer group."""
    conn = get_db_connection()
    query = """
    SELECT pp.company_id, c.company_name, pp.metric, pp.value, pp.percentile_rank, pg.is_benchmark
    FROM peer_percentiles pp
    JOIN companies c ON pp.company_id = c.id
    JOIN peer_groups pg ON pp.company_id = pg.company_id AND pp.peer_group_name = pg.peer_group_name
    WHERE pp.peer_group_name = ? AND pp.year = ?
    ORDER BY pp.company_id, pp.metric
    """
    df = pd.read_sql(query, conn, params=(peer_group_name, year))
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_valuation(ticker: str) -> Dict[str, Any]:
    """Fetch latest valuation multiples, FCF yield, and overvaluation flag for a company."""
    conn = get_db_connection()
    query = """
    SELECT 
        m.company_id,
        m.year,
        m.market_cap_crore,
        m.enterprise_value_crore,
        m.pe_ratio,
        m.pb_ratio,
        m.ev_ebitda,
        m.dividend_yield_pct,
        r.free_cash_flow_cr,
        s.broad_sector
    FROM market_cap m
    LEFT JOIN financial_ratios r ON m.company_id = r.company_id AND m.year = r.year
    LEFT JOIN sectors s ON m.company_id = s.company_id
    WHERE m.company_id = ?
    ORDER BY m.year DESC
    LIMIT 1
    """
    df = pd.read_sql(query, conn, params=(ticker.upper(),))

    if df.empty:
        conn.close()
        return {
            "company_id": ticker.upper(),
            "pe_ratio": None,
            "pb_ratio": None,
            "ev_ebitda": None,
            "fcf_yield_pct": None,
            "market_cap_crore": None,
            "valuation_flag": "Fair",
        }

    row = df.iloc[0]
    pe = row["pe_ratio"]
    mc = row["market_cap_crore"]
    fcf = row["free_cash_flow_cr"]
    sector = row["broad_sector"]

    # FCF Yield
    fcf_yield = round((fcf / mc) * 100.0, 2) if mc and mc > 0 and fcf is not None else None

    # Sector median P/E
    sec_query = """
    SELECT MEDIAN_PE FROM (
        SELECT pe_ratio FROM market_cap m
        JOIN sectors s ON m.company_id = s.company_id
        WHERE s.broad_sector = ? AND m.year = '2024-03' AND m.pe_ratio > 0
    )
    """
    # Fetch all sector P/Es for median
    sec_pes = pd.read_sql(
        "SELECT m.pe_ratio FROM market_cap m JOIN sectors s ON m.company_id = s.company_id WHERE s.broad_sector = ? AND m.year = '2024-03' AND m.pe_ratio > 0",
        conn,
        params=(sector,),
    )
    conn.close()

    sec_med = float(sec_pes["pe_ratio"].median()) if not sec_pes.empty else 25.0

    flag = "Fair"
    if pe and pe > 0:
        if pe > sec_med * 1.5:
            flag = "Caution"
        elif pe < sec_med * 0.7:
            flag = "Discount"

    return {
        "company_id": ticker.upper(),
        "year": row["year"],
        "pe_ratio": pe,
        "pb_ratio": row["pb_ratio"],
        "ev_ebitda": row["ev_ebitda"],
        "dividend_yield_pct": row["dividend_yield_pct"],
        "market_cap_crore": mc,
        "fcf_yield_pct": fcf_yield,
        "sector_median_pe": round(sec_med, 2),
        "valuation_flag": flag,
    }


@st.cache_data(ttl=600)
def get_annual_reports(ticker: str) -> pd.DataFrame:
    """Fetch list of annual report URLs from documents table."""
    conn = get_db_connection()
    query = "SELECT year, annual_report FROM documents WHERE company_id = ? ORDER BY year DESC"
    df = pd.read_sql(query, conn, params=(ticker.upper(),))
    conn.close()
    return df


@st.cache_data(ttl=600)
def get_prosandcons(ticker: str) -> Dict[str, List[str]]:
    """Fetch qualitative pros and cons for a company."""
    conn = get_db_connection()
    query = "SELECT pros, cons FROM prosandcons WHERE company_id = ?"
    df = pd.read_sql(query, conn, params=(ticker.upper(),))
    conn.close()

    pros = []
    cons = []
    if not df.empty:
        for p in df["pros"].dropna():
            if str(p).strip():
                pros.append(str(p).strip())
        for c in df["cons"].dropna():
            if str(c).strip():
                cons.append(str(c).strip())

    return {"pros": pros, "cons": cons}


@st.cache_data(ttl=600)
def get_home_kpis(year: str = "2024-03") -> Dict[str, Any]:
    """Compute executive summary tiles for Home screen:
    Average ROE, Median P/E, Median D/E, Total Companies, Median Rev CAGR 5yr, Debt-Free Companies count.
    """
    conn = get_db_connection()
    query = """
    SELECT 
        r.company_id,
        r.return_on_equity_pct,
        r.debt_to_equity,
        r.revenue_cagr_5yr,
        r.composite_quality_score,
        mc.pe_ratio,
        s.broad_sector
    FROM financial_ratios r
    LEFT JOIN market_cap mc ON r.company_id = mc.company_id AND r.year = mc.year
    LEFT JOIN sectors s ON r.company_id = s.company_id
    WHERE r.year = ?
    """
    df = pd.read_sql(query, conn, params=(year,))
    conn.close()

    if df.empty:
        return {
            "avg_roe": 0.0,
            "median_pe": 0.0,
            "median_de": 0.0,
            "total_companies": 0,
            "median_rev_cagr_5yr": 0.0,
            "debt_free_count": 0,
            "df_universe": pd.DataFrame(),
        }

    avg_roe = round(float(df["return_on_equity_pct"].dropna().mean()), 2)
    median_roe = round(float(df["return_on_equity_pct"].dropna().median()), 2)
    pos_pe = df[df["pe_ratio"] > 0]["pe_ratio"]
    median_pe = round(float(pos_pe.median()), 2) if not pos_pe.empty else 0.0

    # Non-financials D/E median
    non_fin_de = df[df["broad_sector"].astype(str).str.lower() != "financials"]["debt_to_equity"].dropna()
    median_de = round(float(non_fin_de.median()), 2) if not non_fin_de.empty else 0.0

    med_rev_cagr = round(float(df["revenue_cagr_5yr"].dropna().median()), 2)
    debt_free_count = int((df["debt_to_equity"] == 0.0).sum())
    total_companies = len(df["company_id"].unique())

    return {
        "avg_roe": avg_roe,
        "median_roe": median_roe,
        "median_pe": median_pe,
        "median_de": median_de,
        "total_companies": total_companies,
        "median_rev_cagr_5yr": med_rev_cagr,
        "debt_free_count": debt_free_count,
        "df_universe": df,
    }


@st.cache_data(ttl=600)
def get_capital_allocation() -> pd.DataFrame:
    """Fetch capital allocation patterns for all companies."""
    conn = get_db_connection()
    query = """
    SELECT 
        ca.company_id,
        c.company_name,
        COALESCE(s.broad_sector, 'Unknown') AS broad_sector,
        COALESCE(s.sub_sector, 'Unknown') AS sub_sector,
        ca.pattern_label,
        ca.cfo_cr,
        ca.cfi_cr,
        ca.cff_cr,
        ca.fcf_cr,
        mc.market_cap_crore
    FROM capital_allocation ca
    JOIN companies c ON ca.company_id = c.id
    LEFT JOIN sectors s ON ca.company_id = s.company_id
    LEFT JOIN market_cap mc ON ca.company_id = mc.company_id AND ca.year = mc.year
    WHERE ca.year = '2024-03'
    ORDER BY ca.pattern_label, c.company_name
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df
