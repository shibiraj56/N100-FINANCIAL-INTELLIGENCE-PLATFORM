"""
Unit tests for database connection, foreign key enforcement, and schema initialization.
"""

import sqlite3
from src.database.connection import get_connection, init_db


def test_init_db_creates_all_tables(tmp_path):
    test_db = str(tmp_path / "test_nifty.db")
    init_db(db_path=test_db, schema_path="db/schema.sql")

    conn = get_connection(db_path=test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in cursor.fetchall()]

    expected = [
        "companies", "profitandloss", "balancesheet", "cashflow", "analysis",
        "documents", "prosandcons", "sectors", "stock_prices", "financial_ratios",
        "market_cap", "peer_groups"
    ]
    for exp in expected:
        assert exp in tables, f"Expected table {exp} not found in database"


def test_foreign_keys_pragma_enabled(tmp_path):
    test_db = str(tmp_path / "test_nifty.db")
    init_db(db_path=test_db, schema_path="db/schema.sql")

    conn = get_connection(db_path=test_db)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys")
    fk_status = cursor.fetchone()[0]
    assert fk_status == 1, "PRAGMA foreign_keys must be ON"


def test_fk_constraint_enforcement(tmp_path):
    test_db = str(tmp_path / "test_nifty.db")
    init_db(db_path=test_db, schema_path="db/schema.sql")

    conn = get_connection(db_path=test_db)
    cursor = conn.cursor()

    # Inserting orphan child record without parent must fail
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO sectors (company_id, broad_sector) VALUES ('INVALID_TICKER', 'Tech')"
        )
