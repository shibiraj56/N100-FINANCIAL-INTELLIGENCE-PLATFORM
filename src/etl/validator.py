"""
Data Quality Validation Module
Implements all 16 Data Quality (DQ) rules (DQ-01 to DQ-16) for Sprint 1 Data Foundation.
Produces output/validation_failures.csv and reports/validation_failures.csv.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Automated validation engine executing DQ-01 through DQ-16 rules.
    """

    def __init__(self, raw_dfs: Dict[str, pd.DataFrame]):
        self.dfs = raw_dfs
        self.failures: List[Dict[str, Any]] = []

    def log_failure(
        self,
        rule_id: str,
        rule_name: str,
        severity: str,
        table_name: str,
        company_id: Optional[str],
        year: Optional[str],
        field: Optional[str],
        value: Any,
        message: str
    ):
        """Record a validation failure or flag."""
        self.failures.append({
            "rule_id": rule_id,
            "rule_name": rule_name,
            "severity": severity,
            "table_name": table_name,
            "company_id": str(company_id) if company_id is not None else "",
            "year": str(year) if year is not None else "",
            "field": str(field) if field is not None else "",
            "value": str(value) if value is not None else "",
            "message": message
        })

    def validate_all(self) -> pd.DataFrame:
        """Run all 16 DQ rules across loaded DataFrames."""
        self.failures.clear()
        
        # 1. Company PK Uniqueness (DQ-01)
        self._check_dq01_company_pk_uniqueness()

        # 2. Annual PK Uniqueness (DQ-02)
        self._check_dq02_annual_pk_uniqueness()

        # 3. Foreign Key Integrity (DQ-03)
        self._check_dq03_fk_integrity()

        # 4. Balance Sheet Balance (DQ-04)
        self._check_dq04_bs_balance()

        # 5. OPM Cross-Check (DQ-05)
        self._check_dq05_opm_cross_check()

        # 6. Positive Sales (DQ-06)
        self._check_dq06_positive_sales()

        # 7. Year Format (DQ-07)
        self._check_dq07_year_format()

        # 8. Ticker Format (DQ-08)
        self._check_dq08_ticker_format()

        # 9. Net Cash Check (DQ-09)
        self._check_dq09_net_cash()

        # 10. Non-Negative Fixed Assets (DQ-10)
        self._check_dq10_fixed_assets()

        # 11. Tax Rate Range (DQ-11)
        self._check_dq11_tax_rate()

        # 12. Dividend Payout Cap (DQ-12)
        self._check_dq12_dividend_cap()

        # 13. URL Validity (DQ-13)
        self._check_dq13_url_validity()

        # 14. EPS Sign Consistency (DQ-14)
        self._check_dq14_eps_sign()

        # 15. BSE/ASE Balance (ext.) (DQ-15)
        self._check_dq15_bse_balance_strict()

        # 16. Coverage Check (DQ-16)
        self._check_dq16_coverage()

        failures_df = pd.DataFrame(self.failures)
        return failures_df

    def save_failures(self, output_paths: Optional[List[str]] = None) -> pd.DataFrame:
        """Export logged validation failures to CSV."""
        df = pd.DataFrame(self.failures)
        if df.empty:
            df = pd.DataFrame(columns=[
                "rule_id", "rule_name", "severity", "table_name",
                "company_id", "year", "field", "value", "message"
            ])
        
        default_paths = ["output/validation_failures.csv", "reports/validation_failures.csv"]
        paths = output_paths or default_paths

        for p in paths:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            df.to_csv(p, index=False)
            logger.info("Saved validation failures to %s (%d records)", p, len(df))

        return df

    # --- Rule Implementations ---

    def _check_dq01_company_pk_uniqueness(self):
        """DQ-01: Company PK Uniqueness (CRITICAL)"""
        df = self.dfs.get("companies")
        if df is None:
            return
        if "id" in df.columns:
            dups = df[df.duplicated(subset=["id"], keep=False)]
            for _, row in dups.iterrows():
                self.log_failure(
                    "DQ-01", "Company PK Uniqueness", "CRITICAL", "companies",
                    row.get("id"), "", "id", row.get("id"),
                    f"Duplicate company primary key: {row.get('id')}"
                )

    def _check_dq02_annual_pk_uniqueness(self):
        """DQ-02: Annual PK Uniqueness (CRITICAL)"""
        annual_tables = ["profitandloss", "balancesheet", "cashflow", "financial_ratios", "market_cap", "documents"]
        for tbl in annual_tables:
            df = self.dfs.get(tbl)
            if df is None:
                continue
            col_y = "year" if "year" in df.columns else ("Year" if "Year" in df.columns else None)
            if "company_id" in df.columns and col_y:
                dups = df[df.duplicated(subset=["company_id", col_y], keep=False)]
                for _, row in dups.iterrows():
                    self.log_failure(
                        "DQ-02", "Annual PK Uniqueness", "CRITICAL", tbl,
                        row.get("company_id"), row.get(col_y), f"(company_id, {col_y})",
                        f"({row.get('company_id')}, {row.get(col_y)})",
                        f"Duplicate annual primary key in {tbl}"
                    )

    def _check_dq03_fk_integrity(self):
        """DQ-03: FK Integrity (CRITICAL)"""
        comp_df = self.dfs.get("companies")
        if comp_df is None or "id" not in comp_df.columns:
            return
        valid_ids = set(comp_df["id"].dropna().astype(str).str.strip().str.upper())

        for tbl, df in self.dfs.items():
            if tbl == "companies" or df is None:
                continue
            if "company_id" in df.columns:
                orphans = df[~df["company_id"].astype(str).str.strip().str.upper().isin(valid_ids)]
                for _, row in orphans.iterrows():
                    self.log_failure(
                        "DQ-03", "FK Integrity", "CRITICAL", tbl,
                        row.get("company_id"), row.get("year", ""), "company_id",
                        row.get("company_id"),
                        f"Orphan record in {tbl}: company_id '{row.get('company_id')}' not found in companies table"
                    )

    def _check_dq04_bs_balance(self):
        """DQ-04: Balance Sheet Balance < 1% (WARNING)"""
        df = self.dfs.get("balancesheet")
        if df is None:
            return
        if "total_assets" in df.columns and "total_liabilities" in df.columns:
            for _, row in df.iterrows():
                try:
                    assets = float(row.get("total_assets", 0))
                    liab = float(row.get("total_liabilities", 0))
                    if assets > 0:
                        diff_pct = abs(assets - liab) / assets
                        if diff_pct >= 0.01:
                            self.log_failure(
                                "DQ-04", "Balance Sheet Balance", "WARNING", "balancesheet",
                                row.get("company_id"), row.get("year"), "total_assets/total_liabilities",
                                f"A:{assets}, L:{liab}",
                                f"Balance sheet mismatch >= 1%: diff={abs(assets - liab):.2f} ({diff_pct*100:.2f}%)"
                            )
                except (ValueError, TypeError):
                    pass

    def _check_dq05_opm_cross_check(self):
        """DQ-05: OPM Cross-Check (WARNING)"""
        df = self.dfs.get("profitandloss")
        if df is None:
            return
        cols = ["opm_percentage", "operating_profit", "sales"]
        if all(c in df.columns for c in cols):
            for _, row in df.iterrows():
                try:
                    opm = float(row.get("opm_percentage", 0))
                    op = float(row.get("operating_profit", 0))
                    sales = float(row.get("sales", 0))
                    if sales > 0:
                        calc_opm = (op / sales) * 100.0
                        if abs(opm - calc_opm) >= 1.0:
                            self.log_failure(
                                "DQ-05", "OPM Cross-Check", "WARNING", "profitandloss",
                                row.get("company_id"), row.get("year"), "opm_percentage",
                                f"src:{opm:.2f}, calc:{calc_opm:.2f}",
                                f"OPM discrepancy >= 1%: source={opm:.2f}%, computed={calc_opm:.2f}%"
                            )
                except (ValueError, TypeError):
                    pass

    def _check_dq06_positive_sales(self):
        """DQ-06: Positive Sales (WARNING)"""
        df = self.dfs.get("profitandloss")
        if df is None or "sales" not in df.columns:
            return
        for _, row in df.iterrows():
            try:
                sales = float(row.get("sales", 0))
                if sales <= 0:
                    self.log_failure(
                        "DQ-06", "Positive Sales", "WARNING", "profitandloss",
                        row.get("company_id"), row.get("year"), "sales", sales,
                        f"Non-positive sales reported: {sales}"
                    )
            except (ValueError, TypeError):
                pass

    def _check_dq07_year_format(self):
        r"""DQ-07: Year Format matches r'^\d{4}-\d{2}$' (CRITICAL)"""
        for tbl, df in self.dfs.items():
            if df is None:
                continue
            col_y = "year" if "year" in df.columns else ("Year" if "Year" in df.columns else None)
            if col_y:
                for _, row in df.iterrows():
                    val = str(row.get(col_y, "")).strip()
                    if not re.match(r"^\d{4}-\d{2}$", val):
                        self.log_failure(
                            "DQ-07", "Year Format", "CRITICAL", tbl,
                            row.get("company_id", ""), val, col_y, val,
                            f"Year value '{val}' does not conform to 'YYYY-MM' format"
                        )

    def _check_dq08_ticker_format(self):
        """DQ-08: Ticker Format 2-12 chars (CRITICAL)"""
        for tbl, df in self.dfs.items():
            if df is None:
                continue
            tcol = "id" if tbl == "companies" else "company_id"
            if tcol in df.columns:
                for _, row in df.iterrows():
                    ticker = str(row.get(tcol, "")).strip()
                    if not (2 <= len(ticker) <= 12) or not re.match(r"^[A-Z0-9\-&]+$", ticker):
                        self.log_failure(
                            "DQ-08", "Ticker Format", "CRITICAL", tbl,
                            ticker, row.get("year", ""), tcol, ticker,
                            f"Invalid ticker symbol format: '{ticker}'"
                        )

    def _check_dq09_net_cash(self):
        """DQ-09: Net Cash Check |net_cash_flow - (CFO+CFI+CFF)| <= 10 (WARNING)"""
        df = self.dfs.get("cashflow")
        if df is None:
            return
        cols = ["net_cash_flow", "operating_activity", "investing_activity", "financing_activity"]
        if all(c in df.columns for c in cols):
            for _, row in df.iterrows():
                try:
                    ncf = float(row.get("net_cash_flow", 0))
                    cfo = float(row.get("operating_activity", 0))
                    cfi = float(row.get("investing_activity", 0))
                    cff = float(row.get("financing_activity", 0))
                    expected = cfo + cfi + cff
                    if abs(ncf - expected) > 10.0:
                        self.log_failure(
                            "DQ-09", "Net Cash Check", "WARNING", "cashflow",
                            row.get("company_id"), row.get("year"), "net_cash_flow",
                            f"NCF:{ncf}, Sum:{expected}",
                            f"Net cash flow mismatch > 10 Cr: reported={ncf}, component_sum={expected}"
                        )
                except (ValueError, TypeError):
                    pass

    def _check_dq10_fixed_assets(self):
        """DQ-10: Non-Negative Fixed Assets (WARNING)"""
        df = self.dfs.get("balancesheet")
        if df is None or "fixed_assets" not in df.columns:
            return
        for _, row in df.iterrows():
            try:
                fa = float(row.get("fixed_assets", 0))
                if fa < 0:
                    self.log_failure(
                        "DQ-10", "Non-Negative Fixed Assets", "WARNING", "balancesheet",
                        row.get("company_id"), row.get("year"), "fixed_assets", fa,
                        f"Negative fixed assets observed: {fa} (coerced to 0)"
                    )
            except (ValueError, TypeError):
                pass

    def _check_dq11_tax_rate(self):
        """DQ-11: Tax Rate Range 0 <= tax_percentage <= 60 (WARNING)"""
        df = self.dfs.get("profitandloss")
        if df is None or "tax_percentage" not in df.columns:
            return
        for _, row in df.iterrows():
            try:
                val = row.get("tax_percentage")
                if pd.notna(val):
                    tax = float(val)
                    if not (0 <= tax <= 60):
                        self.log_failure(
                            "DQ-11", "Tax Rate Range", "WARNING", "profitandloss",
                            row.get("company_id"), row.get("year"), "tax_percentage", tax,
                            f"Tax rate outside standard range [0, 60]: {tax}%"
                        )
            except (ValueError, TypeError):
                pass

    def _check_dq12_dividend_cap(self):
        """DQ-12: Dividend Payout Cap <= 200% (WARNING)"""
        df = self.dfs.get("profitandloss")
        if df is None or "dividend_payout" not in df.columns:
            return
        for _, row in df.iterrows():
            try:
                val = row.get("dividend_payout")
                if pd.notna(val):
                    payout = float(val)
                    if payout > 200:
                        self.log_failure(
                            "DQ-12", "Dividend Payout Cap", "WARNING", "profitandloss",
                            row.get("company_id"), row.get("year"), "dividend_payout", payout,
                            f"Dividend payout ratio > 200%: {payout}%"
                        )
            except (ValueError, TypeError):
                pass

    def _check_dq13_url_validity(self):
        """DQ-13: URL Validity (documents & companies) (WARNING)"""
        url_regex = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
        # Check documents Annual_Report
        doc_df = self.dfs.get("documents")
        if doc_df is not None and "Annual_Report" in doc_df.columns:
            for _, row in doc_df.iterrows():
                url = str(row.get("Annual_Report", "")).strip()
                if url and url.lower() not in ("nan", "none", "") and not url_regex.match(url):
                    self.log_failure(
                        "DQ-13", "URL Validity", "WARNING", "documents",
                        row.get("company_id"), row.get("year", ""), "Annual_Report", url[:50],
                        f"Malformed Annual_Report URL: {url}"
                    )
        # Check companies URLs
        comp_df = self.dfs.get("companies")
        if comp_df is not None:
            for col in ["website", "nse_profile", "bse_profile"]:
                if col in comp_df.columns:
                    for _, row in comp_df.iterrows():
                        u = str(row.get(col, "")).strip()
                        if u and u.lower() not in ("nan", "none", "") and not url_regex.match(u):
                            self.log_failure(
                                "DQ-13", "URL Validity", "WARNING", "companies",
                                row.get("id"), "", col, u[:50],
                                f"Malformed {col} URL in companies: {u}"
                            )

    def _check_dq14_eps_sign(self):
        """DQ-14: EPS Sign Consistency (WARNING)"""
        df = self.dfs.get("profitandloss")
        if df is None or "net_profit" not in df.columns or "eps" not in df.columns:
            return
        for _, row in df.iterrows():
            try:
                np_val = row.get("net_profit")
                eps_val = row.get("eps")
                if pd.notna(np_val) and pd.notna(eps_val):
                    np_f = float(np_val)
                    eps_f = float(eps_val)
                    if (np_f > 0 and eps_f < 0) or (np_f < 0 and eps_f > 0):
                        self.log_failure(
                            "DQ-14", "EPS Sign Consistency", "WARNING", "profitandloss",
                            row.get("company_id"), row.get("year"), "eps/net_profit",
                            f"NP:{np_f}, EPS:{eps_f}",
                            f"EPS sign mismatch with net profit: NP={np_f}, EPS={eps_f}"
                        )
            except (ValueError, TypeError):
                pass

    def _check_dq15_bse_balance_strict(self):
        """DQ-15: BSE/ASE Strict Balance total_liabilities == total_assets (INFO)"""
        df = self.dfs.get("balancesheet")
        if df is None or "total_assets" not in df.columns or "total_liabilities" not in df.columns:
            return
        for _, row in df.iterrows():
            try:
                assets = float(row.get("total_assets", 0))
                liab = float(row.get("total_liabilities", 0))
                if assets != liab:
                    self.log_failure(
                        "DQ-15", "BSE/ASE Balance (strict)", "INFO", "balancesheet",
                        row.get("company_id"), row.get("year"), "total_assets/total_liabilities",
                        f"Diff: {assets - liab}",
                        f"Non-exact asset/liability match: assets={assets}, liab={liab}"
                    )
            except (ValueError, TypeError):
                pass

    def _check_dq16_coverage(self):
        """DQ-16: Coverage Check - Each company has >= 5 years of records (WARNING)"""
        comp_df = self.dfs.get("companies")
        pl_df = self.dfs.get("profitandloss")
        if comp_df is None or pl_df is None or "company_id" not in pl_df.columns:
            return
        all_comps = comp_df["id"].dropna().unique()
        counts = pl_df["company_id"].value_counts()
        for c in all_comps:
            yr_count = counts.get(c, 0)
            if yr_count < 5:
                self.log_failure(
                    "DQ-16", "Coverage Check", "WARNING", "profitandloss",
                    c, "", "year_coverage", yr_count,
                    f"Company {c} has fewer than 5 years of financial history ({yr_count} years)"
                )
