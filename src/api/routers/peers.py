"""Peer Group & Comparative Radar Router (Epic 11, Day 40)."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
import pandas as pd

from src.api.database import get_db

router = APIRouter(tags=["Peers"])


@router.get("/peers/{group_name}")
def get_peer_group_percentiles(
    group_name: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return all companies in a peer group with percentile ranks across all evaluated metrics."""
    cursor = conn.cursor()
    name_clean = group_name.strip()

    # Query with exact or case-insensitive match
    cursor.execute(
        """
        SELECT pp.*, c.company_name
        FROM peer_percentiles pp
        LEFT JOIN companies c ON pp.company_id = c.id
        WHERE LOWER(pp.peer_group_name) = LOWER(?)
           OR LOWER(REPLACE(pp.peer_group_name, ' ', '')) = LOWER(REPLACE(?, ' ', ''))
        ORDER BY pp.company_id, pp.metric
        """,
        (name_clean, name_clean),
    )
    rows = [dict(r) for r in cursor.fetchall()]

    if not rows:
        raise HTTPException(status_code=404, detail=f"Peer group '{name_clean}' not found.")

    return rows


@router.get("/companies/{ticker}/peers/compare")
def compare_company_peers(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """Return 8-axis radar benchmark data: company metrics vs peer group average vs benchmark constituent."""
    ticker_clean = ticker.strip().upper()
    cursor = conn.cursor()

    # Find peer group of the company
    cursor.execute(
        "SELECT peer_group_name, is_benchmark FROM peer_groups WHERE company_id = ?",
        (ticker_clean,),
    )
    peer_info = cursor.fetchone()
    if not peer_info:
        raise HTTPException(status_code=404, detail=f"Company '{ticker_clean}' has no mapped peer group.")

    group_name = peer_info["peer_group_name"]

    # All companies in peer group
    cursor.execute(
        "SELECT company_id, is_benchmark FROM peer_groups WHERE peer_group_name = ?",
        (group_name,),
    )
    group_members = [dict(r) for r in cursor.fetchall()]
    all_cids = [m["company_id"] for m in group_members]
    bench_cids = [m["company_id"] for m in group_members if m["is_benchmark"] == 1]
    benchmark_cid = bench_cids[0] if bench_cids else all_cids[0]

    placeholders = ",".join(["?"] * len(all_cids))
    query = f"""
        SELECT 
            c.id AS company_id,
            r.return_on_equity_pct AS roe,
            r.roce_pct AS roce,
            r.operating_profit_margin_pct AS opm,
            r.net_profit_margin_pct AS npm,
            r.revenue_cagr_5yr AS rev_cagr,
            r.pat_cagr_5yr AS pat_cagr,
            r.debt_to_equity AS de,
            r.asset_turnover AS asset_turnover
        FROM companies c
        LEFT JOIN (
            SELECT * FROM financial_ratios 
            WHERE year != 'TTM' AND (return_on_equity_pct IS NOT NULL OR operating_profit_margin_pct IS NOT NULL)
            ORDER BY year DESC
        ) r ON c.id = r.company_id
        WHERE c.id IN ({placeholders})
        GROUP BY c.id
    """
    cursor.execute(query, tuple(all_cids))
    metrics_rows = [dict(r) for r in cursor.fetchall()]
    df = pd.DataFrame(metrics_rows)

    radar_axes = [
        "ROE %",
        "ROCE %",
        "OPM %",
        "NPM %",
        "5Y Rev CAGR",
        "5Y PAT CAGR",
        "Debt/Equity",
        "Asset Turnover",
    ]
    db_cols = ["roe", "roce", "opm", "npm", "rev_cagr", "pat_cagr", "de", "asset_turnover"]

    company_row = df[df["company_id"] == ticker_clean]
    bench_row = df[df["company_id"] == benchmark_cid]

    comp_vals = [round(float(company_row[c].iloc[0]), 2) if not company_row.empty and pd.notna(company_row[c].iloc[0]) else 0.0 for c in db_cols]
    bench_vals = [round(float(bench_row[c].iloc[0]), 2) if not bench_row.empty and pd.notna(bench_row[c].iloc[0]) else 0.0 for c in db_cols]
    peer_avg_vals = [round(float(df[c].dropna().mean()), 2) if not df[c].dropna().empty else 0.0 for c in db_cols]

    return {
        "ticker": ticker_clean,
        "peer_group_name": group_name,
        "benchmark_ticker": benchmark_cid,
        "axes": radar_axes,
        "company_values": comp_vals,
        "peer_average_values": peer_avg_vals,
        "benchmark_values": bench_vals,
    }
