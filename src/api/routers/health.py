"""Health & System Status Router (Epic 11, Day 38)."""

from __future__ import annotations

import time
from fastapi import APIRouter, Depends
import sqlite3
from typing import Any, Dict

from src.api.database import get_db

router = APIRouter(tags=["Health"])

START_TIME = time.time()

CORE_TABLES = [
    "companies",
    "profitandloss",
    "balancesheet",
    "cashflow",
    "analysis",
    "documents",
    "prosandcons",
    "sectors",
    "stock_prices",
    "market_cap",
]


@router.get("/health")
def health_check(conn: sqlite3.Connection = Depends(get_db)) -> Dict[str, Any]:
    """Return platform status, database table row counts, uptime, and system version."""
    cursor = conn.cursor()
    row_counts: Dict[str, int] = {}

    for table in CORE_TABLES:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            cnt = cursor.fetchone()[0]
            row_counts[table] = cnt
        except Exception:
            row_counts[table] = 0

    uptime = round(time.time() - START_TIME, 2)

    return {
        "status": "ok",
        "version": "1.0.0",
        "uptime_seconds": uptime,
        "db_row_counts": row_counts,
    }
