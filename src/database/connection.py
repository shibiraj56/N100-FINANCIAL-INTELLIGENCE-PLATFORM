"""
Database Connection and Initialization Module
Ensures PRAGMA foreign_keys = ON on every connection.
"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Returns an SQLite connection with PRAGMA foreign_keys = ON enabled.
    """
    target_path = db_path or DEFAULT_DB_PATH
    Path(target_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None, schema_path: str = "db/schema.sql") -> None:
    """
    Executes the DDL statements in schema.sql to initialize all tables and indexes.
    """
    target_path = db_path or DEFAULT_DB_PATH
    with open(schema_path, "r", encoding="utf-8") as f:
        ddl = f.read()

    with get_connection(target_path) as conn:
        conn.executescript(ddl)
        conn.commit()
    logger.info("Database initialized successfully at %s using %s", target_path, schema_path)
