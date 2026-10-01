"""Unit tests for DataLoader, schema verification, and table integrity (Epic 01 / Day 41).

Verifies correct row counts and expected column schemas for each of the core tables.
"""

import sqlite3
import pytest
from src.database.connection import get_connection

DB_PATH = "data/nifty100.db"


@pytest.fixture(scope="module")
def db_conn():
    conn = get_connection(DB_PATH)
    yield conn
    conn.close()


def test_01_companies_table_schema_and_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA table_info(companies)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"id", "company_name", "about_company", "website"}.issubset(cols)
    assert cur.execute("SELECT COUNT(*) FROM companies").fetchone()[0] == 92


def test_02_profitandloss_schema_and_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA table_info(profitandloss)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"company_id", "year", "sales", "operating_profit", "net_profit"}.issubset(cols)
    assert cur.execute("SELECT COUNT(*) FROM profitandloss").fetchone()[0] == 1276


def test_03_balancesheet_schema_and_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA table_info(balancesheet)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"company_id", "year", "borrowings", "total_assets"}.issubset(cols)
    assert cur.execute("SELECT COUNT(*) FROM balancesheet").fetchone()[0] == 1312


def test_04_cashflow_schema_and_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA table_info(cashflow)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"company_id", "year", "operating_activity", "investing_activity", "financing_activity"}.issubset(cols)
    assert cur.execute("SELECT COUNT(*) FROM cashflow").fetchone()[0] == 1187


def test_05_stock_prices_schema_and_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA table_info(stock_prices)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"company_id", "date", "open_price", "close_price", "volume"}.issubset(cols)
    assert cur.execute("SELECT COUNT(*) FROM stock_prices").fetchone()[0] == 5520


def test_06_market_cap_schema_and_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA table_info(market_cap)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"company_id", "year", "market_cap_crore", "pe_ratio"}.issubset(cols)
    assert cur.execute("SELECT COUNT(*) FROM market_cap").fetchone()[0] == 552


def test_07_sectors_schema_and_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA table_info(sectors)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"company_id", "broad_sector", "sub_sector"}.issubset(cols)
    assert cur.execute("SELECT COUNT(*) FROM sectors").fetchone()[0] == 92


def test_08_documents_schema_and_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA table_info(documents)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"company_id", "year", "annual_report"}.issubset(cols)
    assert cur.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1585


def test_09_prosandcons_schema_and_count(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA table_info(prosandcons)")
    cols = {row[1] for row in cur.fetchall()}
    assert {"id", "company_id", "pros", "cons"}.issubset(cols)
    assert cur.execute("SELECT COUNT(*) FROM prosandcons").fetchone()[0] > 0


def test_10_foreign_key_integrity_clean(db_conn):
    cur = db_conn.cursor()
    cur.execute("PRAGMA foreign_key_check;")
    violations = cur.fetchall()
    assert len(violations) == 0, f"Expected 0 foreign key violations, found: {len(violations)}"
