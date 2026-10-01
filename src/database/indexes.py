"""Database Index Optimization Engine (Epic 12, Day 43).

Creates composite B-tree indexes across all high-volume tables to accelerate
REST API queries, screener scans, and analytical aggregations.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sqlite3
import sys

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(root_dir, "data", "nifty100.db")
if not os.path.exists(DEFAULT_DB_PATH) and os.path.exists(os.path.join(root_dir, "nifty100.db")):
    DEFAULT_DB_PATH = os.path.join(root_dir, "nifty100.db")

INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_ratios_comp_yr ON financial_ratios(company_id, year);",
    "CREATE INDEX IF NOT EXISTS idx_pl_comp_yr ON profitandloss(company_id, year);",
    "CREATE INDEX IF NOT EXISTS idx_bs_comp_yr ON balancesheet(company_id, year);",
    "CREATE INDEX IF NOT EXISTS idx_cf_comp_yr ON cashflow(company_id, year);",
    "CREATE INDEX IF NOT EXISTS idx_sp_comp_dt ON stock_prices(company_id, date);",
    "CREATE INDEX IF NOT EXISTS idx_mc_comp_yr ON market_cap(company_id, year);",
    "CREATE INDEX IF NOT EXISTS idx_sectors_comp ON sectors(company_id);",
    "CREATE INDEX IF NOT EXISTS idx_sectors_broad ON sectors(broad_sector);",
    "CREATE INDEX IF NOT EXISTS idx_peer_groups_comp ON peer_groups(company_id);",
    "CREATE INDEX IF NOT EXISTS idx_peer_groups_name ON peer_groups(peer_group_name);",
    "CREATE INDEX IF NOT EXISTS idx_peer_percentiles_group ON peer_percentiles(peer_group_name);",
    "CREATE INDEX IF NOT EXISTS idx_documents_comp ON documents(company_id);",
]


def apply_indexes(db_path: str = DEFAULT_DB_PATH) -> int:
    """Create all performance B-tree indexes on SQLite database."""
    conn = sqlite3.connect(db_path)
    count = 0
    try:
        cursor = conn.cursor()
        for stmt in INDEX_STATEMENTS:
            cursor.execute(stmt)
            count += 1
        conn.commit()
        # Also run PRAGMA optimize
        cursor.execute("PRAGMA optimize;")
        logger.info(f"Successfully verified/created {count} performance indexes on {db_path}")
    finally:
        conn.close()
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    apply_indexes()
