"""Database Connection & Session Dependency for FastAPI Server."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, Generator, List

root_dir = str(Path(__file__).resolve().parent.parent.parent)

DEFAULT_DB_PATH = os.path.join(root_dir, "data", "nifty100.db")
if not os.path.exists(DEFAULT_DB_PATH) and os.path.exists(os.path.join(root_dir, "nifty100.db")):
    DEFAULT_DB_PATH = os.path.join(root_dir, "nifty100.db")


def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI Dependency for database connections."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def query_all(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute query and return list of dictionaries."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def query_one(query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    """Execute query and return single dictionary or None."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
