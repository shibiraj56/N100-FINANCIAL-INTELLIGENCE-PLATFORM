"""Sector Benchmarking & Constituent Router (Epic 11, Day 40)."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
import numpy as np
import pandas as pd

from src.api.database import get_db

router = APIRouter(prefix="/sectors", tags=["Sectors"])


@router.get("")
def list_sectors(conn: sqlite3.Connection = Depends(get_db)) -> List[Dict[str, Any]]:
    """Return all 11 peer group sectors with constituent counts and median KPI benchmarks."""
    cursor = conn.cursor()

    # Query peer groups, ratios and valuation
    query = """
        SELECT 
            pg.peer_group_name AS sector_name,
            c.id AS company_id,
            r.return_on_equity_pct,
            r.debt_to_equity,
            mc.pe_ratio
        FROM peer_groups pg
        JOIN companies c ON pg.company_id = c.id
        LEFT JOIN (
            SELECT company_id, return_on_equity_pct, debt_to_equity,
                   ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY year DESC) as rn
            FROM financial_ratios
            WHERE year != 'TTM' AND (return_on_equity_pct IS NOT NULL OR debt_to_equity IS NOT NULL)
        ) r ON c.id = r.company_id AND r.rn = 1
        LEFT JOIN (
            SELECT company_id, pe_ratio,
                   ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY year DESC) as rn
            FROM market_cap
        ) mc ON c.id = mc.company_id AND mc.rn = 1
    """
    cursor.execute(query)
    rows = [dict(r) for r in cursor.fetchall()]

    if not rows:
        return []

    df = pd.DataFrame(rows)
    sector_summary = []

    for name, group in df.groupby("sector_name"):
        med_roe = group["return_on_equity_pct"].dropna().median()
        med_pe = group["pe_ratio"].dropna().median()
        med_de = group["debt_to_equity"].dropna().median()

        sector_summary.append({
            "sector": name,
            "company_count": len(group),
            "median_roe": round(float(med_roe), 2) if pd.notna(med_roe) else None,
            "median_pe": round(float(med_pe), 2) if pd.notna(med_pe) else None,
            "median_de": round(float(med_de), 2) if pd.notna(med_de) else None,
        })

    sector_summary.sort(key=lambda s: s["sector"])
    return sector_summary


@router.get("/{sector}/companies")
def get_sector_companies(
    sector: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return all companies in a sector or peer group with their latest year financial KPIs."""
    sector_clean = sector.strip()
    cursor = conn.cursor()

    # Match by peer_group_name or broad_sector
    query_peer = """
        SELECT pg.company_id
        FROM peer_groups pg
        WHERE LOWER(pg.peer_group_name) = LOWER(?)
           OR LOWER(REPLACE(pg.peer_group_name, ' ', '')) = LOWER(REPLACE(?, ' ', ''))
    """
    cursor.execute(query_peer, (sector_clean, sector_clean))
    cids = [r[0] for r in cursor.fetchall()]

    if not cids:
        # Try matching broad_sector or common abbreviations (e.g. IT -> Information Technology)
        query_sec = """
            SELECT company_id
            FROM sectors
            WHERE LOWER(broad_sector) = LOWER(?)
               OR LOWER(REPLACE(broad_sector, ' ', '')) = LOWER(REPLACE(?, ' ', ''))
               OR (LOWER(?) IN ('it', 'tech') AND LOWER(broad_sector) = 'information technology')
               OR (LOWER(?) = 'auto' AND LOWER(broad_sector) = 'consumer discretionary')
        """
        cursor.execute(query_sec, (sector_clean, sector_clean, sector_clean, sector_clean))
        cids = [r[0] for r in cursor.fetchall()]

    if not cids:
        raise HTTPException(status_code=404, detail=f"Sector or peer group '{sector_clean}' not found.")

    placeholders = ",".join(["?"] * len(cids))
    detail_query = f"""
        SELECT 
            c.id AS ticker,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            r.return_on_equity_pct,
            r.roce_pct,
            r.debt_to_equity,
            r.operating_profit_margin_pct,
            r.revenue_cagr_5yr,
            r.free_cash_flow_cr,
            mc.market_cap_crore,
            mc.pe_ratio,
            mc.pb_ratio
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT company_id, return_on_equity_pct, roce_pct, debt_to_equity,
                   operating_profit_margin_pct, revenue_cagr_5yr, free_cash_flow_cr,
                   ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY year DESC) as rn
            FROM financial_ratios
            WHERE year != 'TTM' AND (return_on_equity_pct IS NOT NULL OR operating_profit_margin_pct IS NOT NULL)
        ) r ON c.id = r.company_id AND r.rn = 1
        LEFT JOIN (
            SELECT company_id, market_cap_crore, pe_ratio, pb_ratio,
                   ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY year DESC) as rn
            FROM market_cap
        ) mc ON c.id = mc.company_id AND mc.rn = 1
        WHERE c.id IN ({placeholders})
        ORDER BY c.id ASC
    """
    cursor.execute(detail_query, tuple(cids))
    rows = [dict(r) for r in cursor.fetchall()]
    return rows
