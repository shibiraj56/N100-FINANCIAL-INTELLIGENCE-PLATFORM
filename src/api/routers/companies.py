"""Company Financial Data & Statements Router (Epic 11, Day 39)."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from src.api.database import get_db

router = APIRouter(prefix="/companies", tags=["Companies"])

root_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
TEARSHEETS_DIR = os.path.join(root_dir, "reports", "tearsheets")


@router.get("")
def list_companies(
    sector: Optional[str] = Query(None, description="Filter by broad sector"),
    market_cap_category: Optional[str] = Query(None, description="Filter by market cap category"),
    search: Optional[str] = Query(None, description="Search ticker or company name"),
    conn: sqlite3.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return all tracked companies with sector and latest profitability metrics."""
    cursor = conn.cursor()

    query = """
        SELECT 
            c.id, 
            c.company_name, 
            s.broad_sector, 
            s.sub_sector,
            s.market_cap_category,
            r.return_on_equity_pct AS roe_pct,
            r.roce_pct AS roce_pct
        FROM companies c
        LEFT JOIN sectors s ON c.id = s.company_id
        LEFT JOIN (
            SELECT company_id, return_on_equity_pct, roce_pct,
                   ROW_NUMBER() OVER (PARTITION BY company_id ORDER BY year DESC) as rn
            FROM financial_ratios
            WHERE year != 'TTM' AND (return_on_equity_pct IS NOT NULL OR operating_profit_margin_pct IS NOT NULL)
        ) r ON c.id = r.company_id AND r.rn = 1
        WHERE 1=1
    """
    params: List[Any] = []

    if sector:
        query += " AND LOWER(s.broad_sector) = LOWER(?)"
        params.append(sector)

    if market_cap_category:
        query += " AND LOWER(s.market_cap_category) = LOWER(?)"
        params.append(market_cap_category)

    if search:
        search_pattern = f"%{search.strip().lower()}%"
        query += " AND (LOWER(c.id) LIKE ? OR LOWER(c.company_name) LIKE ?)"
        params.extend([search_pattern, search_pattern])

    query += " ORDER BY c.id ASC"
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/{ticker}")
def get_company_profile(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> Dict[str, Any]:
    """Return full company profile: corporate metadata, sector classification, and latest KPIs."""
    ticker_clean = ticker.strip().upper()
    cursor = conn.cursor()

    # Company info
    cursor.execute("SELECT * FROM companies WHERE id = ?", (ticker_clean,))
    comp_row = cursor.fetchone()
    if not comp_row:
        raise HTTPException(status_code=404, detail=f"Company ticker '{ticker_clean}' not found.")

    company_data = dict(comp_row)

    # Sector info
    cursor.execute("SELECT broad_sector, sub_sector FROM sectors WHERE company_id = ?", (ticker_clean,))
    sec_row = cursor.fetchone()
    if sec_row:
        company_data.update(dict(sec_row))

    # Latest ratios
    cursor.execute(
        """
        SELECT * FROM financial_ratios 
        WHERE company_id = ? AND year != 'TTM'
        ORDER BY year DESC LIMIT 1
        """,
        (ticker_clean,),
    )
    ratios_row = cursor.fetchone()
    company_data["latest_ratios"] = dict(ratios_row) if ratios_row else {}

    # Market Cap valuation
    cursor.execute(
        """
        SELECT market_cap_crore, pe_ratio, pb_ratio, dividend_yield_pct 
        FROM market_cap 
        WHERE company_id = ? 
        ORDER BY year DESC LIMIT 1
        """,
        (ticker_clean,),
    )
    mc_row = cursor.fetchone()
    company_data["latest_valuation"] = dict(mc_row) if mc_row else {}

    return company_data


@router.get("/{ticker}/pl")
def get_profit_and_loss(
    ticker: str,
    from_year: Optional[str] = Query(None, description="Start year in YYYY-MM format"),
    to_year: Optional[str] = Query(None, description="End year in YYYY-MM format"),
    conn: sqlite3.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return historical Profit & Loss statements for the specified ticker."""
    ticker_clean = ticker.strip().upper()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM companies WHERE id = ?", (ticker_clean,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Company ticker '{ticker_clean}' not found.")

    query = "SELECT * FROM profitandloss WHERE company_id = ?"
    params: List[Any] = [ticker_clean]

    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)

    query += " ORDER BY year ASC"
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


@router.get("/{ticker}/bs")
def get_balance_sheet(
    ticker: str,
    from_year: Optional[str] = Query(None, description="Start year in YYYY-MM format"),
    to_year: Optional[str] = Query(None, description="End year in YYYY-MM format"),
    conn: sqlite3.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return historical Balance Sheet statements for the specified ticker."""
    ticker_clean = ticker.strip().upper()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM companies WHERE id = ?", (ticker_clean,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Company ticker '{ticker_clean}' not found.")

    query = "SELECT * FROM balancesheet WHERE company_id = ?"
    params: List[Any] = [ticker_clean]

    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)

    query += " ORDER BY year ASC"
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


@router.get("/{ticker}/cashflow")
def get_cash_flow(
    ticker: str,
    from_year: Optional[str] = Query(None, description="Start year in YYYY-MM format"),
    to_year: Optional[str] = Query(None, description="End year in YYYY-MM format"),
    conn: sqlite3.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return historical Cash Flow statements for the specified ticker."""
    ticker_clean = ticker.strip().upper()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM companies WHERE id = ?", (ticker_clean,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Company ticker '{ticker_clean}' not found.")

    query = "SELECT * FROM cashflow WHERE company_id = ?"
    params: List[Any] = [ticker_clean]

    if from_year:
        query += " AND year >= ?"
        params.append(from_year)
    if to_year:
        query += " AND year <= ?"
        params.append(to_year)

    query += " ORDER BY year ASC"
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


@router.get("/{ticker}/ratios")
def get_financial_ratios(
    ticker: str,
    year: Optional[str] = Query(None, description="Specific fiscal year in YYYY-MM format or TTM"),
    conn: sqlite3.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return computed financial KPIs and ratios across all years or for a single year."""
    ticker_clean = ticker.strip().upper()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM companies WHERE id = ?", (ticker_clean,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Company ticker '{ticker_clean}' not found.")

    query = "SELECT * FROM financial_ratios WHERE company_id = ?"
    params: List[Any] = [ticker_clean]

    if year:
        query += " AND year = ?"
        params.append(year)

    query += " ORDER BY year ASC"
    cursor.execute(query, tuple(params))
    return [dict(row) for row in cursor.fetchall()]


@router.get("/{ticker}/tearsheet")
def download_tearsheet(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> FileResponse:
    """Download the pre-generated 2-page institutional PDF tearsheet for the company."""
    ticker_clean = ticker.strip().upper()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM companies WHERE id = ?", (ticker_clean,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Company ticker '{ticker_clean}' not found.")

    pdf_path = os.path.join(TEARSHEETS_DIR, f"{ticker_clean}_tearsheet.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail=f"Tearsheet PDF for '{ticker_clean}' not found on server.")

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{ticker_clean}_tearsheet.pdf",
    )
