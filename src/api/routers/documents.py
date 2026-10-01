"""Regulatory Documents & Annual Reports Router (Epic 11, Day 40)."""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException

from src.api.database import get_db

router = APIRouter(tags=["Documents"])


def validate_url(url: Optional[str]) -> bool:
    """Validate whether URL has valid http/https scheme and netloc."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


@router.get("/companies/{ticker}/documents")
def get_company_documents(
    ticker: str,
    conn: sqlite3.Connection = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Return historical annual report links with an is_url_valid validation boolean flag."""
    ticker_clean = ticker.strip().upper()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM companies WHERE id = ?", (ticker_clean,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Company '{ticker_clean}' not found.")

    cursor.execute(
        "SELECT id, company_id, year, annual_report FROM documents WHERE company_id = ? ORDER BY year DESC",
        (ticker_clean,),
    )
    rows = cursor.fetchall()

    results = []
    for r in rows:
        d = dict(r)
        url = d.get("annual_report")
        d["is_url_valid"] = validate_url(url)
        results.append(d)

    return results
