"""Financial Screener & Filter Engine.

Implements multi-criteria stock screening across all 92 Nifty 100 companies,
supporting 15 filterable metrics, 6 preset screeners, YAML configuration loading,
sector-relative P10/P90 winsorised scoring, and Financials sector D/E carve-outs.
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import yaml

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(root_dir, "config", "screener_config.yaml")
DEFAULT_DB_PATH = os.path.join(root_dir, "data", "nifty100.db")


def winsorize_series(s: pd.Series, lower_p: float = 10.0, upper_p: float = 90.0) -> pd.Series:
    """Winsorize numeric series between lower_p and upper_p percentiles."""
    valid = s.dropna()
    if len(valid) < 3:
        return s
    p_low = np.percentile(valid, lower_p)
    p_high = np.percentile(valid, upper_p)
    return s.clip(lower=p_low, upper=p_high)


def scale_0_to_100(s: pd.Series, invert: bool = False) -> pd.Series:
    """Min-max scale a series to 0-100 range."""
    valid = s.dropna()
    if len(valid) < 2 or (valid.max() == valid.min()):
        return pd.Series(50.0, index=s.index)
    scaled = (s - valid.min()) / (valid.max() - valid.min()) * 100.0
    if invert:
        scaled = 100.0 - scaled
    return scaled.round(1)


class ScreenerEngine:
    """Core screener and multi-criteria filtering engine."""

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        config_path: str = DEFAULT_CONFIG_PATH,
    ):
        self.db_path = db_path
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not os.path.exists(self.config_path):
            logger.warning("Config file not found at %s. Using default empty config.", self.config_path)
            return {"presets": {}, "composite_scoring": {}}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get_universe_data(self, year: str = "2024-03") -> pd.DataFrame:
        """Fetch unified screening dataset joining financial_ratios, companies, sectors, P&L, and market_cap.

        Returns a comprehensive DataFrame for all 92 companies for the specified fiscal year.
        """
        conn = sqlite3.connect(self.db_path)
        query = """
        SELECT 
            r.company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            r.year,
            pl.sales,
            pl.operating_profit,
            pl.net_profit,
            r.operating_profit_margin_pct,
            r.net_profit_margin_pct,
            r.return_on_equity_pct,
            r.roce_pct,
            r.roa_pct,
            r.debt_to_equity,
            r.interest_coverage,
            r.icr_label,
            r.net_debt_cr,
            r.asset_turnover,
            r.free_cash_flow_cr,
            r.capex_cr,
            r.earnings_per_share,
            r.book_value_per_share,
            r.dividend_payout_ratio_pct,
            r.revenue_cagr_3yr,
            r.revenue_cagr_5yr,
            r.revenue_cagr_10yr,
            r.pat_cagr_3yr,
            r.pat_cagr_5yr,
            r.eps_cagr_5yr,
            r.cfo_quality_score,
            r.capex_intensity_pct,
            r.fcf_conversion_pct,
            r.capital_allocation_pattern,
            r.composite_quality_score,
            mc.market_cap_crore,
            mc.enterprise_value_crore,
            mc.pe_ratio,
            mc.pb_ratio,
            mc.ev_ebitda,
            mc.dividend_yield_pct
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.id
        LEFT JOIN sectors s ON r.company_id = s.company_id
        LEFT JOIN profitandloss pl ON r.company_id = pl.company_id AND r.year = pl.year
        LEFT JOIN market_cap mc ON r.company_id = mc.company_id AND r.year = mc.year
        WHERE r.year = ?
        """
        df = pd.read_sql(query, conn, params=(year,))

        # Also get prior year D/E to calculate YoY change
        prior_year = "2023-03" if "2024" in year else "2022-03"
        df_prior = pd.read_sql(
            "SELECT company_id, debt_to_equity AS de_prior FROM financial_ratios WHERE year = ?",
            conn,
            params=(prior_year,),
        )
        df = pd.merge(df, df_prior, on="company_id", how="left")
        df["de_change_yoy"] = df["debt_to_equity"] - df["de_prior"]

        conn.close()

        # Add sector-relative composite scores
        df = self.compute_sector_relative_scores(df)

        return df

    def fetch_universe(self, year: str = "2024-03") -> pd.DataFrame:
        """Alias for get_universe_data."""
        return self.get_universe_data(year=year)

    def compute_sector_relative_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute sector-relative composite scores using P10/P90 winsorization within each broad_sector."""
        df = df.copy()
        df["sector_composite_score"] = df["composite_quality_score"]

        # If broad_sector is present, compute within-sector normalized score
        if "broad_sector" in df.columns:
            sector_scores = []
            for sector, group in df.groupby("broad_sector"):
                if len(group) >= 3:
                    # Winsorize key metrics within sector
                    roe_w = winsorize_series(group["return_on_equity_pct"])
                    roce_w = winsorize_series(group["roce_pct"])
                    fcf_w = winsorize_series(group["free_cash_flow_cr"])
                    rev_w = winsorize_series(group["revenue_cagr_5yr"])

                    s_roe = scale_0_to_100(roe_w)
                    s_roce = scale_0_to_100(roce_w)
                    s_fcf = scale_0_to_100(fcf_w)
                    s_rev = scale_0_to_100(rev_w)

                    # Sector-relative composite
                    sec_score = (
                        0.30 * s_roe + 0.25 * s_roce + 0.25 * s_fcf + 0.20 * s_rev
                    ).round(1)
                    group_res = group.copy()
                    group_res["sector_composite_score"] = sec_score
                    sector_scores.append(group_res)
                else:
                    sector_scores.append(group.copy())
            df = pd.concat(sector_scores, ignore_index=True)

        return df

    def apply_filters(
        self, df: pd.DataFrame, filter_criteria: Dict[str, Any]
    ) -> pd.DataFrame:
        """Apply multi-criteria filters to the DataFrame.

        Supports all 15 filterable metrics plus compound conditions.
        """
        filtered = df.copy()

        # 1. ROE min
        if "roe_min" in filter_criteria and filter_criteria["roe_min"] is not None:
            filtered = filtered[filtered["return_on_equity_pct"] >= filter_criteria["roe_min"]]

        # 2. D/E max (Automatically skip companies in Financials sector, unless de_max is 0.0)
        if "de_max" in filter_criteria and filter_criteria["de_max"] is not None:
            max_de = filter_criteria["de_max"]
            if max_de == 0.0:
                filtered = filtered[filtered["debt_to_equity"] == 0.0]
            else:
                is_fin = filtered["broad_sector"].astype(str).str.lower() == "financials"
                is_valid_de = filtered["debt_to_equity"] <= max_de
                filtered = filtered[is_fin | is_valid_de]

        # 3. FCF min
        if "fcf_min" in filter_criteria and filter_criteria["fcf_min"] is not None:
            filtered = filtered[filtered["free_cash_flow_cr"] >= filter_criteria["fcf_min"]]

        # 4. Revenue CAGR 5yr min
        if "rev_cagr_5yr_min" in filter_criteria and filter_criteria["rev_cagr_5yr_min"] is not None:
            filtered = filtered[filtered["revenue_cagr_5yr"] >= filter_criteria["rev_cagr_5yr_min"]]

        # 5. PAT CAGR 5yr min
        if "pat_cagr_5yr_min" in filter_criteria and filter_criteria["pat_cagr_5yr_min"] is not None:
            filtered = filtered[filtered["pat_cagr_5yr"] >= filter_criteria["pat_cagr_5yr_min"]]

        # 6. OPM min
        if "opm_min" in filter_criteria and filter_criteria["opm_min"] is not None:
            filtered = filtered[filtered["operating_profit_margin_pct"] >= filter_criteria["opm_min"]]

        # 7. P/E max
        if "pe_max" in filter_criteria and filter_criteria["pe_max"] is not None:
            max_pe = filter_criteria["pe_max"]
            filtered = filtered[(filtered["pe_ratio"] > 0) & (filtered["pe_ratio"] <= max_pe)]

        # 8. P/B max
        if "pb_max" in filter_criteria and filter_criteria["pb_max"] is not None:
            max_pb = filter_criteria["pb_max"]
            filtered = filtered[(filtered["pb_ratio"] > 0) & (filtered["pb_ratio"] <= max_pb)]

        # 9. Dividend Yield min
        if "div_yield_min" in filter_criteria and filter_criteria["div_yield_min"] is not None:
            filtered = filtered[filtered["dividend_yield_pct"] >= filter_criteria["div_yield_min"]]

        # 10. ICR min (Treat 'Debt Free' or D/E = 0 as infinity — always passes)
        if "icr_min" in filter_criteria and filter_criteria["icr_min"] is not None:
            min_icr = filter_criteria["icr_min"]
            is_debt_free = (
                filtered["icr_label"].astype(str).str.lower().str.contains("debt free")
                | (filtered["debt_to_equity"] == 0.0)
            )
            passes_icr = filtered["interest_coverage"] >= min_icr
            filtered = filtered[is_debt_free | passes_icr]

        # 11. Market Cap min
        if "market_cap_min" in filter_criteria and filter_criteria["market_cap_min"] is not None:
            filtered = filtered[filtered["market_cap_crore"] >= filter_criteria["market_cap_min"]]

        # 12. Net Profit min
        if "net_profit_min" in filter_criteria and filter_criteria["net_profit_min"] is not None:
            filtered = filtered[filtered["net_profit"] >= filter_criteria["net_profit_min"]]

        # 13. EPS CAGR min
        if "eps_cagr_min" in filter_criteria and filter_criteria["eps_cagr_min"] is not None:
            filtered = filtered[filtered["eps_cagr_5yr"] >= filter_criteria["eps_cagr_min"]]

        # 14. Asset Turnover min
        if "asset_turnover_min" in filter_criteria and filter_criteria["asset_turnover_min"] is not None:
            filtered = filtered[filtered["asset_turnover"] >= filter_criteria["asset_turnover_min"]]

        # 15. Sales min
        if "sales_min" in filter_criteria and filter_criteria["sales_min"] is not None:
            filtered = filtered[filtered["sales"] >= filter_criteria["sales_min"]]

        # Optional extra filters
        if "dividend_payout_max" in filter_criteria and filter_criteria["dividend_payout_max"] is not None:
            filtered = filtered[filtered["dividend_payout_ratio_pct"] <= filter_criteria["dividend_payout_max"]]

        if "rev_cagr_3yr_min" in filter_criteria and filter_criteria["rev_cagr_3yr_min"] is not None:
            filtered = filtered[filtered["revenue_cagr_3yr"] >= filter_criteria["rev_cagr_3yr_min"]]

        if filter_criteria.get("de_declining_yoy"):
            # D/E is declining year-over-year: de_t < de_{t-1} or debt_to_equity == 0
            filtered = filtered[
                (filtered["debt_to_equity"] < filtered["de_prior"]) | (filtered["debt_to_equity"] == 0.0)
            ]

        return filtered

    def rank_and_sort(
        self,
        df: pd.DataFrame,
        sort_by: str = "composite_quality_score",
        ascending: bool = False,
    ) -> pd.DataFrame:
        """Rank and sort screened results by score or metric."""
        if df.empty:
            return df
        if sort_by in df.columns:
            return df.sort_values(by=sort_by, ascending=ascending)
        return df

    def run_preset(self, preset_name: str, year: str = "2024-03") -> pd.DataFrame:
        """Run a preset screen defined in screener_config.yaml."""
        presets = self.config.get("presets", {})
        if preset_name not in presets:
            raise KeyError(f"Unknown screener preset: '{preset_name}'. Available: {list(presets.keys())}")

        preset = presets[preset_name]
        filters = preset.get("filters", {})
        sort_by = preset.get("sort_by", "composite_quality_score")
        sort_asc = preset.get("sort_ascending", False)

        df_universe = self.get_universe_data(year=year)
        results = self.apply_filters(df_universe, filters)

        if sort_by in results.columns:
            results = results.sort_values(by=sort_by, ascending=sort_asc)

        return results

    # Convenience helper methods for the 6 canonical presets
    def run_quality_compounder(self, year: str = "2024-03") -> pd.DataFrame:
        """ROE > 15%, D/E < 1.0 (Financials skipped), FCF > 0, Revenue CAGR 5yr > 10%."""
        return self.run_preset("quality_compounder", year=year)

    def run_value_pick(self, year: str = "2024-03") -> pd.DataFrame:
        """P/E < 25, P/B < 5.0, D/E < 2.0, Dividend Yield > 1%."""
        return self.run_preset("value_pick", year=year)

    def run_growth_accelerator(self, year: str = "2024-03") -> pd.DataFrame:
        """PAT CAGR 5yr > 20%, Revenue CAGR 5yr > 15%, D/E < 2.0."""
        return self.run_preset("growth_accelerator", year=year)

    def run_dividend_champion(self, year: str = "2024-03") -> pd.DataFrame:
        """Dividend Yield > 2%, Dividend Payout < 80%, FCF > 0."""
        return self.run_preset("dividend_champion", year=year)

    def run_debt_free_blue_chip(self, year: str = "2024-03") -> pd.DataFrame:
        """D/E = 0, ROE > 12%, Revenue > 5000 Crore."""
        return self.run_preset("debt_free_blue_chip", year=year)

    def run_turnaround_watch(self, year: str = "2024-03") -> pd.DataFrame:
        """Revenue CAGR 3yr > 10%, FCF positive latest year, D/E declining YoY."""
        return self.run_preset("turnaround_watch", year=year)

    def run_all_presets(self, year: str = "2024-03") -> Dict[str, pd.DataFrame]:
        """Execute all 6 presets and return dict mapping preset_name -> DataFrame."""
        presets = self.config.get("presets", {})
        results: Dict[str, pd.DataFrame] = {}
        for p_name in presets.keys():
            results[p_name] = self.run_preset(p_name, year=year)
            logger.info("Preset %-22s: %2d companies returned", p_name, len(results[p_name]))
        return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    engine = ScreenerEngine()
    all_res = engine.run_all_presets()
    print("\nScreener Engine Summary:")
    for name, df_res in all_res.items():
        print(f"- {name:22s}: {len(df_res)} companies")
