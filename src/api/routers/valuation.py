"""Market Cap Valuation & Multiples Router (Epic 11, Day 40)."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException

from src.api.database import get_db

router = APIRouter(prefix="/market-cap", tags=["Valuation"])


@router.get("/{ticker}")
def get_historical_market_cap_multiples(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return historical valuation multiples (P/E, P/B, EV/EBITDA, Dividend Yield) from 2019 to 2024."""
    ticker_clean = ticker.strip().upper()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM companies WHERE id = ?", (ticker_clean,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Company '{ticker_clean}' not found.")

    query = """
        SELECT 
            year,
            market_cap_crore,
            enterprise_value_crore,
            pe_ratio,
            pb_ratio,
            ev_ebitda,
            dividend_yield_pct
        FROM market_cap
        WHERE company_id = ?
        ORDER BY year ASC
    """
    cursor.execute(query, (ticker_clean,))
    rows = [dict(r) for r in cursor.fetchall()]
    return rows
