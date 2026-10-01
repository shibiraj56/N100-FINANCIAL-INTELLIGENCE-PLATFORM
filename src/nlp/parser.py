"""NLP Analysis Text Parser (Epic 09, Day 29).

Parses qualitative CAGR and metric strings from analysis.xlsx / SQLite analysis table using regex.
Extracts period and percentage numbers into output/analysis_parsed.csv,
logs unmatched phrases to output/parse_failures.csv,
and cross-validates parsed CAGR values against computed CAGRs in financial_ratios.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(root_dir, "data", "nifty100.db")

# Regex to extract period and percentage: e.g. "10 Years: 21%", "5 Years: 13%", "1 Year: 13%"
CAGR_REGEX = re.compile(r"(\d+)\s*Years?:?\s*(-?[\d.]+)%", re.IGNORECASE)

TARGET_FIELDS = [
    ("compounded_sales_growth", "sales_cagr"),
    ("compounded_profit_growth", "profit_cagr"),
    ("stock_price_cagr", "stock_price_cagr"),
    ("roe", "roe"),
]


class AnalysisParser:
    """Parses and cross-validates qualitative growth metrics from the analysis repository."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.parsed_records: List[Dict[str, Any]] = []
        self.failures: List[Dict[str, Any]] = []
        self.divergences: List[Dict[str, Any]] = []

    def load_analysis_data(self) -> pd.DataFrame:
        """Fetch raw analysis table from SQLite or fallback to Excel."""
        conn = sqlite3.connect(self.db_path)
        try:
            df = pd.read_sql("SELECT * FROM analysis", conn)
        finally:
            conn.close()
        return df

    def parse_entry(
        self, company_id: str, field_name: str, metric_type: str, text: Any
    ) -> Optional[Dict[str, Any]]:
        """Parse a single text entry using regex."""
        if text is None or pd.isna(text) or not str(text).strip():
            self.failures.append({
                "company_id": company_id,
                "field_name": field_name,
                "raw_text": text,
                "reason": "Empty or Null text",
            })
            return None

        clean_text = str(text).strip()
        matches = list(CAGR_REGEX.finditer(clean_text))
        if matches:
            last_record = None
            for match in matches:
                period = int(match.group(1))
                val = float(match.group(2))
                record = {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period,
                    "value_pct": val,
                }
                self.parsed_records.append(record)
                last_record = record
            return last_record
        else:
            self.failures.append({
                "company_id": company_id,
                "field_name": field_name,
                "raw_text": clean_text,
                "reason": "Does not match pattern (e.g. TTM / non-standard format)",
            })
            return None

    def run_parser(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Parse all fields across all records in analysis dataset."""
        df = self.load_analysis_data()
        self.parsed_records.clear()
        self.failures.clear()

        for _, row in df.iterrows():
            cid = row["company_id"]
            for col_name, m_type in TARGET_FIELDS:
                if col_name in row:
                    self.parse_entry(cid, col_name, m_type, row[col_name])

        df_parsed = pd.DataFrame(self.parsed_records)
        df_failures = pd.DataFrame(self.failures)
        return df_parsed, df_failures

    def cross_validate_cagrs(self, df_parsed: pd.DataFrame) -> pd.DataFrame:
        """Cross-validate parsed CAGRs against computed CAGRs from the Ratio Engine.
        
        Flags divergence > 5% for manual review.
        """
        conn = sqlite3.connect(self.db_path)
        # Fetch latest computed ratios (FY 2024)
        query = """
        SELECT company_id, revenue_cagr_3yr, revenue_cagr_5yr, revenue_cagr_10yr,
               pat_cagr_3yr, pat_cagr_5yr, return_on_equity_pct
        FROM financial_ratios
        WHERE year = '2024-03'
        """
        df_fr = pd.read_sql(query, conn)
        conn.close()

        divergence_records: List[Dict[str, Any]] = []

        for _, row in df_parsed.iterrows():
            cid = row["company_id"]
            m_type = row["metric_type"]
            period = row["period_years"]
            parsed_val = row["value_pct"]

            co_fr = df_fr[df_fr["company_id"] == cid]
            if co_fr.empty:
                continue

            computed_val = None
            if m_type == "sales_cagr":
                if period == 3:
                    computed_val = co_fr.iloc[0]["revenue_cagr_3yr"]
                elif period == 5:
                    computed_val = co_fr.iloc[0]["revenue_cagr_5yr"]
                elif period == 10:
                    computed_val = co_fr.iloc[0]["revenue_cagr_10yr"]
            elif m_type == "profit_cagr":
                if period == 3:
                    computed_val = co_fr.iloc[0]["pat_cagr_3yr"]
                elif period == 5:
                    computed_val = co_fr.iloc[0]["pat_cagr_5yr"]

            if computed_val is not None and pd.notna(computed_val):
                diff = abs(parsed_val - computed_val)
                is_divergent = diff > 5.0
                divergence_records.append({
                    "company_id": cid,
                    "metric_type": m_type,
                    "period_years": period,
                    "parsed_value_pct": parsed_val,
                    "computed_value_pct": round(computed_val, 2),
                    "divergence_pct": round(diff, 2),
                    "flagged_for_review": is_divergent,
                })

        df_div = pd.DataFrame(divergence_records)
        self.divergences = divergence_records
        return df_div

    def save_artifacts(
        self,
        output_parsed_path: str = "output/analysis_parsed.csv",
        output_failures_path: str = "output/parse_failures.csv",
        output_divergence_path: str = "output/cagr_divergence.csv",
    ) -> Tuple[str, str, str]:
        """Execute full parsing pipeline and save artifacts."""
        df_parsed, df_failures = self.run_parser()
        df_div = self.cross_validate_cagrs(df_parsed)

        os.makedirs(os.path.dirname(output_parsed_path), exist_ok=True)
        df_parsed.to_csv(output_parsed_path, index=False)
        df_failures.to_csv(output_failures_path, index=False)
        df_div.to_csv(output_divergence_path, index=False)

        logger.info(
            "Saved parsed records to %s (%d rows), failures to %s (%d rows), divergence to %s (%d rows)",
            output_parsed_path, len(df_parsed), output_failures_path, len(df_failures), output_divergence_path, len(df_div)
        )
        return output_parsed_path, output_failures_path, output_divergence_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = AnalysisParser()
    p_path, f_path, d_path = parser.save_artifacts()
    print("Parsed output:", p_path)
    print("Failures output:", f_path)
    print("Divergence output:", d_path)
