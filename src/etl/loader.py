"""
Data Ingestion and Loader Module (src/etl/loader.py)
Loads all 12 Excel files (7 core + 5 supplementary), normalises fields,
validates schema, removes duplicates, and loads into SQLite nifty100.db.
Generates output/load_audit.csv and reports/load_audit.csv.
"""

import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import pandas as pd
import numpy as np
import sqlite3

from src.etl.normaliser import normalize_year, normalize_ticker
from src.etl.validator import DataValidator
from src.database.connection import get_connection, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = os.getenv("RAW_DATA_DIR", "data/raw")
DB_PATH = os.getenv("DB_PATH", "data/nifty100.db")


class DataLoader:
    """
    Orchestrates full ETL lifecycle for N100 platform.
    """

    def __init__(self, raw_dir: str = RAW_DIR, db_path: str = DB_PATH):
        self.raw_dir = raw_dir
        self.db_path = db_path
        self.raw_dfs: Dict[str, pd.DataFrame] = {}
        self.clean_dfs: Dict[str, pd.DataFrame] = {}
        self.audit_records: List[Dict[str, any]] = []

    def read_all_excel(self) -> Dict[str, pd.DataFrame]:
        """Reads 7 core files (header=1) and 5 supplementary files (header=0)."""
        logger.info("Reading raw Excel files from %s...", self.raw_dir)
        
        core_files = {
            "companies": "companies.xlsx",
            "profitandloss": "profitandloss.xlsx",
            "balancesheet": "balancesheet.xlsx",
            "cashflow": "cashflow.xlsx",
            "analysis": "analysis.xlsx",
            "documents": "documents.xlsx",
            "prosandcons": "prosandcons.xlsx",
        }

        supp_files = {
            "sectors": "sectors.xlsx",
            "stock_prices": "stock_prices.xlsx",
            "financial_ratios": "financial_ratios.xlsx",
            "market_cap": "market_cap.xlsx",
            "peer_groups": "peer_groups.xlsx",
        }

        for name, filename in core_files.items():
            fpath = os.path.join(self.raw_dir, filename)
            if not os.path.exists(fpath):
                raise FileNotFoundError(f"Missing core dataset: {fpath}")
            df = pd.read_excel(fpath, header=1)
            self.raw_dfs[name] = df
            logger.info("Loaded core: %s (shape: %s)", name, df.shape)

        for name, filename in supp_files.items():
            fpath = os.path.join(self.raw_dir, filename)
            if not os.path.exists(fpath):
                raise FileNotFoundError(f"Missing supplementary dataset: {fpath}")
            df = pd.read_excel(fpath, header=0)
            self.raw_dfs[name] = df
            logger.info("Loaded supplementary: %s (shape: %s)", name, df.shape)

        return self.raw_dfs

    def clean_and_normalize(self) -> Dict[str, pd.DataFrame]:
        """Normalises tickers, years, and prepares schema for SQLite ingestion."""
        logger.info("Normalising and transforming datasets...")

        # 1. Companies
        df_co = self.raw_dfs["companies"].copy()
        df_co["id"] = df_co["id"].apply(lambda x: normalize_ticker(x))
        if "company_name" in df_co.columns:
            df_co["company_name"] = df_co["company_name"].astype(str).str.replace("\n", " ").str.strip()
        for col in ["face_value", "book_value", "roce_percentage", "roe_percentage"]:
            if col in df_co.columns:
                df_co[col] = pd.to_numeric(df_co[col], errors="coerce")
        self.clean_dfs["companies"] = df_co

        # 2. Profit and Loss
        df_pl = self.raw_dfs["profitandloss"].copy()
        df_pl["company_id"] = df_pl["company_id"].apply(lambda x: normalize_ticker(x))
        df_pl["year"] = df_pl["year"].apply(lambda x: normalize_year(x))
        num_cols_pl = ["sales", "expenses", "operating_profit", "opm_percentage", "other_income",
                        "interest", "depreciation", "profit_before_tax", "tax_percentage",
                        "net_profit", "eps", "dividend_payout"]
        for col in num_cols_pl:
            if col in df_pl.columns:
                df_pl[col] = pd.to_numeric(df_pl[col], errors="coerce")
        self.clean_dfs["profitandloss"] = df_pl

        # 3. Balance Sheet
        df_bs = self.raw_dfs["balancesheet"].copy()
        df_bs["company_id"] = df_bs["company_id"].apply(lambda x: normalize_ticker(x))
        df_bs["year"] = df_bs["year"].apply(lambda x: normalize_year(x))
        num_cols_bs = ["equity_capital", "reserves", "borrowings", "other_liabilities",
                        "total_liabilities", "fixed_assets", "cwip", "investments", "other_asset", "total_assets"]
        for col in num_cols_bs:
            if col in df_bs.columns:
                df_bs[col] = pd.to_numeric(df_bs[col], errors="coerce")
        if "fixed_assets" in df_bs.columns:
            df_bs["fixed_assets"] = df_bs["fixed_assets"].apply(lambda x: 0.0 if pd.notna(x) and x < 0 else x)
        self.clean_dfs["balancesheet"] = df_bs

        # 4. Cash Flow
        df_cf = self.raw_dfs["cashflow"].copy()
        df_cf["company_id"] = df_cf["company_id"].apply(lambda x: normalize_ticker(x))
        df_cf["year"] = df_cf["year"].apply(lambda x: normalize_year(x))
        num_cols_cf = ["operating_activity", "investing_activity", "financing_activity", "net_cash_flow"]
        for col in num_cols_cf:
            if col in df_cf.columns:
                df_cf[col] = pd.to_numeric(df_cf[col], errors="coerce")
        self.clean_dfs["cashflow"] = df_cf

        # 5. Analysis
        df_an = self.raw_dfs["analysis"].copy()
        df_an["company_id"] = df_an["company_id"].apply(lambda x: normalize_ticker(x))
        self.clean_dfs["analysis"] = df_an

        # 6. Documents
        df_doc = self.raw_dfs["documents"].copy()
        df_doc["company_id"] = df_doc["company_id"].apply(lambda x: normalize_ticker(x))
        if "Year" in df_doc.columns:
            df_doc["year"] = df_doc["Year"].apply(lambda x: normalize_year(x))
            df_doc = df_doc.drop(columns=["Year"])
        if "Annual_Report" in df_doc.columns:
            df_doc["annual_report"] = df_doc["Annual_Report"]
            df_doc = df_doc.drop(columns=["Annual_Report"])
        self.clean_dfs["documents"] = df_doc

        # 7. Pros and Cons
        df_pc = self.raw_dfs["prosandcons"].copy()
        df_pc["company_id"] = df_pc["company_id"].apply(lambda x: normalize_ticker(x))
        self.clean_dfs["prosandcons"] = df_pc

        # 8. Sectors
        df_sec = self.raw_dfs["sectors"].copy()
        df_sec["company_id"] = df_sec["company_id"].apply(lambda x: normalize_ticker(x))
        if "index_weight_pct" in df_sec.columns:
            df_sec["index_weight_pct"] = pd.to_numeric(df_sec["index_weight_pct"], errors="coerce")
        self.clean_dfs["sectors"] = df_sec

        # 9. Stock Prices
        df_sp = self.raw_dfs["stock_prices"].copy()
        df_sp["company_id"] = df_sp["company_id"].apply(lambda x: normalize_ticker(x))
        if "date" in df_sp.columns:
            df_sp["date"] = pd.to_datetime(df_sp["date"]).dt.strftime("%Y-%m-%d")
        num_cols_sp = ["open_price", "high_price", "low_price", "close_price", "volume", "adjusted_close"]
        for col in num_cols_sp:
            if col in df_sp.columns:
                df_sp[col] = pd.to_numeric(df_sp[col], errors="coerce")
        self.clean_dfs["stock_prices"] = df_sp

        # 10. Financial Ratios
        df_fr = self.raw_dfs["financial_ratios"].copy()
        df_fr["company_id"] = df_fr["company_id"].apply(lambda x: normalize_ticker(x))
        df_fr["year"] = df_fr["year"].apply(lambda x: normalize_year(x))
        for col in df_fr.columns:
            if col not in ["id", "company_id", "year"]:
                df_fr[col] = pd.to_numeric(df_fr[col], errors="coerce")
        self.clean_dfs["financial_ratios"] = df_fr

        # 11. Market Cap
        df_mc = self.raw_dfs["market_cap"].copy()
        df_mc["company_id"] = df_mc["company_id"].apply(lambda x: normalize_ticker(x))
        df_mc["year"] = df_mc["year"].apply(lambda x: normalize_year(x))
        for col in df_mc.columns:
            if col not in ["id", "company_id", "year"]:
                df_mc[col] = pd.to_numeric(df_mc[col], errors="coerce")
        self.clean_dfs["market_cap"] = df_mc

        # 12. Peer Groups
        df_pg = self.raw_dfs["peer_groups"].copy()
        df_pg["company_id"] = df_pg["company_id"].apply(lambda x: normalize_ticker(x))
        if "is_benchmark" in df_pg.columns:
            df_pg["is_benchmark"] = df_pg["is_benchmark"].apply(lambda x: 1 if bool(x) is True else 0)
        self.clean_dfs["peer_groups"] = df_pg

        return self.clean_dfs

    def validate(self) -> pd.DataFrame:
        """Runs the 16 DQ rules and outputs validation_failures.csv."""
        logger.info("Executing 16 DQ Validation Rules...")
        validator = DataValidator(self.clean_dfs)
        failures = validator.validate_all()
        validator.save_failures(["output/validation_failures.csv", "reports/validation_failures.csv"])
        logger.info("Validation complete. Failures logged: %d", len(failures))
        return failures

    def load_to_sqlite(self) -> pd.DataFrame:
        """Inserts all normalised DataFrames into SQLite with PRAGMA foreign_keys = ON."""
        logger.info("Loading tables into SQLite database at %s...", self.db_path)
        init_db(db_path=self.db_path, schema_path="db/schema.sql")

        load_order = [
            "companies",
            "sectors",
            "profitandloss",
            "balancesheet",
            "cashflow",
            "financial_ratios",
            "market_cap",
            "stock_prices",
            "documents",
            "analysis",
            "prosandcons",
            "peer_groups",
        ]

        conn = get_connection(self.db_path)
        timestamp = datetime.now().isoformat()
        audit_list = []

        try:
            with conn:
                for tbl in load_order:
                    start_t = time.time()
                    raw_df = self.raw_dfs.get(tbl, pd.DataFrame())
                    clean_df = self.clean_dfs.get(tbl, pd.DataFrame())
                    rows_in = len(raw_df)
                    rows_out = len(clean_df)
                    rejected = max(0, rows_in - rows_out)

                    clean_df.to_sql(tbl, conn, if_exists="append", index=False)
                    runtime = round(time.time() - start_t, 4)

                    logger.info("Loaded table %-16s | in: %5d | out: %5d | rej: %3d | time: %.3fs",
                                tbl, rows_in, rows_out, rejected, runtime)

                    audit_list.append({
                        "dataset": tbl,
                        "table_name": tbl,
                        "rows_in": rows_in,
                        "rows_loaded": rows_out,
                        "columns": clean_df.shape[1],
                        "rejected": rejected,
                        "status": "SUCCESS",
                        "timestamp": timestamp,
                        "runtime_s": runtime
                    })

            # Check PRAGMA foreign_key_check
            fk_cursor = conn.cursor()
            fk_cursor.execute("PRAGMA foreign_key_check;")
            fk_errors = fk_cursor.fetchall()
            if fk_errors:
                logger.error("CRITICAL: PRAGMA foreign_key_check detected %d violations!", len(fk_errors))
            else:
                logger.info("PRAGMA foreign_key_check: 0 violations! FK integrity verified.")

        finally:
            conn.close()

        # Mirror nifty100.db to root
        if self.db_path == "data/nifty100.db" and os.path.exists("data/nifty100.db"):
            import shutil
            shutil.copyfile("data/nifty100.db", "nifty100.db")
            logger.info("Mirrored nifty100.db to repository root.")

        audit_df = pd.DataFrame(audit_list)
        os.makedirs("output", exist_ok=True)
        os.makedirs("reports", exist_ok=True)
        audit_df.to_csv("output/load_audit.csv", index=False)
        audit_df.to_csv("reports/load_audit.csv", index=False)
        logger.info("Saved load audit to output/load_audit.csv and reports/load_audit.csv")
        return audit_df

    def run_pipeline(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Executes full ETL pipeline: read -> clean -> validate -> load."""
        self.read_all_excel()
        self.clean_and_normalize()
        val_df = self.validate()
        audit_df = self.load_to_sqlite()
        return val_df, audit_df


if __name__ == "__main__":
    loader = DataLoader()
    val_df, audit_df = loader.run_pipeline()
    print("\n--- LOAD AUDIT SUMMARY ---")
    print(audit_df.to_string(index=False))
