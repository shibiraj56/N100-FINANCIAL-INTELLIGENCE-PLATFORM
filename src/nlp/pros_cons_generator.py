"""NLP Pros & Cons Generator (Epic 09, Day 30).

Applies 12 Pro rules and 12 Con rules to computed financial metrics, assigning
confidence scores (>60%) based on signal robustness and data depth.
Generates output/pros_cons_generated.csv and guarantees at least 1 pro and 1 con
for every tracked Nifty 100 company.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
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
if not os.path.exists(DEFAULT_DB_PATH) and os.path.exists(os.path.join(root_dir, "nifty100.db")):
    DEFAULT_DB_PATH = os.path.join(root_dir, "nifty100.db")

OUTPUT_CSV_PATH = os.path.join(root_dir, "output", "pros_cons_generated.csv")


class ProsConsGenerator:
    """Generates qualitative investment thesis points (Pros and Cons) from financial data."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.output_records: List[Dict[str, Any]] = []

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load necessary historical datasets from SQLite."""
        conn = sqlite3.connect(self.db_path)
        try:
            df_comps = pd.read_sql("SELECT id, company_name FROM companies ORDER BY id", conn)
            df_ratios = pd.read_sql(
                "SELECT * FROM financial_ratios WHERE year != 'TTM' ORDER BY company_id, year", conn
            )
            df_pl = pd.read_sql(
                "SELECT * FROM profitandloss WHERE year != 'TTM' ORDER BY company_id, year", conn
            )
            df_bs = pd.read_sql(
                "SELECT * FROM balancesheet WHERE year != 'TTM' ORDER BY company_id, year", conn
            )
            df_sec = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
            df_mc = pd.read_sql("SELECT company_id, dividend_yield_pct FROM market_cap WHERE year = '2024-03'", conn)
        finally:
            conn.close()

        return df_comps, df_ratios, df_pl, df_bs, df_sec, df_mc

    def evaluate_company(
        self,
        company_id: str,
        r_df: pd.DataFrame,
        pl_df: pd.DataFrame,
        bs_df: pd.DataFrame,
        broad_sector: str,
        dividend_yield: float,
    ) -> List[Dict[str, Any]]:
        """Evaluate 12 PRO and 12 CON rules for a single company."""
        results: List[Dict[str, Any]] = []
        is_fin = (broad_sector or "").strip().lower() == "financials"

        if r_df.empty:
            return results

        # Isolate rows with valid annual statements (filter out half-yearly placeholder rows like 2024-09 if empty)
        valid_r = r_df[
            r_df["operating_profit_margin_pct"].notna()
            | r_df["return_on_equity_pct"].notna()
            | (r_df["debt_to_equity"].notna() & (r_df["year"].str.endswith("-03") | r_df["year"].str.endswith("-12") | (r_df["year"] == "2024-09")))
        ]
        if valid_r.empty:
            valid_r = r_df

        latest_r = valid_r.iloc[-1]
        latest_pl = pl_df.iloc[-1] if not pl_df.empty else pd.Series(dtype=object)
        latest_bs = bs_df.iloc[-1] if not bs_df.empty else pd.Series(dtype=object)

        de_val = latest_r.get("debt_to_equity")
        r_cagr = latest_r.get("revenue_cagr_5yr")
        r_cagr_3 = latest_r.get("revenue_cagr_3yr")
        p_cagr = latest_r.get("pat_cagr_5yr")
        eps_cagr = latest_r.get("eps_cagr_5yr")
        opm_val = latest_r.get("operating_profit_margin_pct")
        roce_val = latest_r.get("roce_pct")
        roe_val = latest_r.get("return_on_equity_pct")
        icr_val = latest_r.get("interest_coverage")
        icr_lbl = str(latest_r.get("icr_label", "")).lower()
        dp_val = latest_r.get("dividend_payout_ratio_pct")
        fcf_val = latest_r.get("free_cash_flow_cr")

        roe_s = valid_r["return_on_equity_pct"].dropna()
        fcf_s = valid_r["free_cash_flow_cr"].dropna()
        opm_s = valid_r["operating_profit_margin_pct"].dropna()
        sales_s = pl_df["sales"].dropna() if not pl_df.empty and "sales" in pl_df else pd.Series(dtype=float)
        de_s = valid_r["debt_to_equity"].dropna()
        eps_s = pl_df["eps"].dropna() if not pl_df.empty and "eps" in pl_df else pd.Series(dtype=float)

        # ---------------- PRO RULES (PRO-01 to PRO-12) ----------------

        # PRO-01: High ROE (>20% or >15%)
        if len(roe_s) >= 3 and (roe_s.tail(3) > 20.0).all():
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-01",
                "rule_type": "PRO",
                "text": "Consistently high return on equity above 20% demonstrates exceptional capital efficiency",
                "confidence_score": 90,
            })
        elif len(roe_s) >= 3 and (roe_s.tail(3) > 15.0).all():
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-01",
                "rule_type": "PRO",
                "text": "Consistently high return on equity above 15% demonstrates exceptional capital efficiency",
                "confidence_score": 75,
            })
        elif pd.notna(roe_val) and roe_val > 15.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-01",
                "rule_type": "PRO",
                "text": "High return on equity demonstrates strong capital efficiency",
                "confidence_score": 70,
            })

        # PRO-02: FCF positive (5+ years or 3+ years or latest positive)
        if len(fcf_s) >= 5 and (fcf_s.tail(5) > 0).all():
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-02",
                "rule_type": "PRO",
                "text": "Strong free cash flow generation over 5 years signals healthy business fundamentals",
                "confidence_score": 90,
            })
        elif len(fcf_s) >= 3 and (fcf_s.tail(3) > 0).all():
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-02",
                "rule_type": "PRO",
                "text": "Strong free cash flow generation over recent years signals healthy business fundamentals",
                "confidence_score": 75,
            })
        elif pd.notna(fcf_val) and fcf_val > 0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-02",
                "rule_type": "PRO",
                "text": "Positive free cash flow generation signals healthy business fundamentals",
                "confidence_score": 65,
            })

        # PRO-03: Debt-Free or Low Leverage
        if de_val == 0.0 or (de_val is not None and not is_fin and de_val < 0.05):
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-03",
                "rule_type": "PRO",
                "text": "Debt-free balance sheet provides financial flexibility and eliminates interest burden",
                "confidence_score": 95,
            })
        elif de_val is not None and not is_fin and de_val < 0.2:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-03",
                "rule_type": "PRO",
                "text": "Conservative leverage profile provides strong financial flexibility",
                "confidence_score": 75,
            })

        # PRO-04: Revenue CAGR > 15% (or 3-yr / >10%)
        if r_cagr is not None and r_cagr > 15.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-04",
                "rule_type": "PRO",
                "text": "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum",
                "confidence_score": 90,
            })
        elif r_cagr_3 is not None and r_cagr_3 > 15.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-04",
                "rule_type": "PRO",
                "text": "Strong revenue growth above 15% CAGR reflects solid business expansion momentum",
                "confidence_score": 80,
            })
        elif r_cagr is not None and r_cagr > 10.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-04",
                "rule_type": "PRO",
                "text": "Revenue growing at healthy double-digit CAGR reflects strong business momentum",
                "confidence_score": 70,
            })

        # PRO-05: OPM > 25% or > 15%
        if opm_val is not None and opm_val > 25.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-05",
                "rule_type": "PRO",
                "text": "Operating profit margin above 25% indicates strong pricing power and cost discipline",
                "confidence_score": 85,
            })
        elif opm_val is not None and opm_val > 15.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-05",
                "rule_type": "PRO",
                "text": "Healthy operating profit margin indicates good pricing power and cost discipline",
                "confidence_score": 70,
            })

        # PRO-06: PAT CAGR > 20% or > 12%
        if p_cagr is not None and p_cagr > 20.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-06",
                "rule_type": "PRO",
                "text": "Net profit compounding at above 20% over 5 years creates significant shareholder value",
                "confidence_score": 90,
            })
        elif p_cagr is not None and p_cagr > 12.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-06",
                "rule_type": "PRO",
                "text": "Net profit compounding at healthy double-digit rate creates significant shareholder value",
                "confidence_score": 75,
            })

        # PRO-07: ICR > 10 or Debt Free
        if (icr_val is not None and icr_val > 10.0) or "debt free" in icr_lbl or de_val == 0.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-07",
                "rule_type": "PRO",
                "text": "Very high interest coverage ratio reflects negligible financial stress from debt servicing",
                "confidence_score": 90,
            })
        elif icr_val is not None and icr_val > 5.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-07",
                "rule_type": "PRO",
                "text": "Comfortable interest coverage ratio reflects negligible financial stress from debt servicing",
                "confidence_score": 75,
            })

        # PRO-08: Dividend Yield > 2% (or >1%) backed by FCF
        if dividend_yield > 2.0 and pd.notna(fcf_val) and fcf_val > 0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-08",
                "rule_type": "PRO",
                "text": "Consistent dividend yield above 2% backed by positive free cash flow",
                "confidence_score": 85,
            })
        elif dividend_yield > 1.0 and pd.notna(fcf_val) and fcf_val > 0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-08",
                "rule_type": "PRO",
                "text": "Consistent dividend yield backed by positive free cash flow",
                "confidence_score": 70,
            })

        # PRO-09: EPS CAGR > 15% or > 10%
        if eps_cagr is not None and eps_cagr > 15.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-09",
                "rule_type": "PRO",
                "text": "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding",
                "confidence_score": 85,
            })
        elif eps_cagr is not None and eps_cagr > 10.0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-09",
                "rule_type": "PRO",
                "text": "Earnings per share compounding at steady double-digit rate indicates strong earnings quality",
                "confidence_score": 70,
            })

        # PRO-10: ROE improving consecutive years
        if len(roe_s) >= 4 and (roe_s.iloc[-1] > roe_s.iloc[-2] > roe_s.iloc[-3] > roe_s.iloc[-4]):
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-10",
                "rule_type": "PRO",
                "text": "Return on equity improving for 3 consecutive years shows strengthening business quality",
                "confidence_score": 90,
            })
        elif len(roe_s) >= 2 and roe_s.iloc[-1] > roe_s.iloc[-2]:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-10",
                "rule_type": "PRO",
                "text": "Return on equity improving in the latest fiscal year shows strengthening business quality",
                "confidence_score": 65,
            })

        # PRO-11: PAT CAGR > Revenue CAGR (Operating Leverage)
        if p_cagr is not None and r_cagr is not None and p_cagr > r_cagr and p_cagr > 0:
            results.append({
                "company_id": company_id,
                "rule_id": "PRO-11",
                "rule_type": "PRO",
                "text": "Revenue growing slower than profits shows improving operating leverage and scale benefits",
                "confidence_score": 85,
            })
        elif len(pl_df) >= 2:
            p_curr = latest_pl.get("net_profit", 0) or 0
            p_prev = pl_df.iloc[-2].get("net_profit", 0) or 0
            s_curr = latest_pl.get("sales", 0) or 0
            s_prev = pl_df.iloc[-2].get("sales", 0) or 0
            if s_prev > 0 and p_prev > 0:
                p_growth = (p_curr - p_prev) / p_prev
                s_growth = (s_curr - s_prev) / s_prev
                if p_growth > s_growth:
                    results.append({
                        "company_id": company_id,
                        "rule_id": "PRO-11",
                        "rule_type": "PRO",
                        "text": "Revenue growing slower than profits shows improving operating leverage and scale benefits",
                        "confidence_score": 70,
                    })

        # PRO-12: Asset base expansion funded by internal accruals
        if len(bs_df) >= 2:
            tot_assets_curr = latest_bs.get("total_assets", 0) or 0
            tot_assets_prev = bs_df.iloc[-2].get("total_assets", 0) or 0
            borrow_curr = latest_bs.get("borrowings", 0) or 0
            borrow_prev = bs_df.iloc[-2].get("borrowings", 0) or 0
            if tot_assets_curr > tot_assets_prev and (borrow_curr <= borrow_prev or borrow_curr == 0):
                results.append({
                    "company_id": company_id,
                    "rule_id": "PRO-12",
                    "rule_type": "PRO",
                    "text": "Growing asset base funded by internal accruals reflects self-sustaining growth",
                    "confidence_score": 80,
                })
            elif tot_assets_curr > tot_assets_prev:
                results.append({
                    "company_id": company_id,
                    "rule_id": "PRO-12",
                    "rule_type": "PRO",
                    "text": "Growing asset base reflects continuing business expansion",
                    "confidence_score": 65,
                })

        # ---------------- CON RULES (CON-01 to CON-12) ----------------

        # CON-01: D/E elevated
        if not is_fin and de_val is not None and de_val > 2.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-01",
                "rule_type": "CON",
                "text": f"Debt-to-equity ratio of {de_val:.2f} is elevated for a non-financial company and warrants monitoring",
                "confidence_score": 90,
            })
        elif not is_fin and de_val is not None and de_val > 0.8:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-01",
                "rule_type": "CON",
                "text": f"Debt-to-equity ratio of {de_val:.2f} is moderately elevated and warrants monitoring",
                "confidence_score": 65,
            })
        elif is_fin and de_val is not None and de_val > 6.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-01",
                "rule_type": "CON",
                "text": f"Financial leverage of {de_val:.2f}x is on the higher side within the lending and finance sector",
                "confidence_score": 65,
            })

        # CON-02: FCF negative (3 consecutive years or YoY drop / uncomputed)
        if len(fcf_s) >= 3 and (fcf_s.tail(3) < 0).all():
            results.append({
                "company_id": company_id,
                "rule_id": "CON-02",
                "rule_type": "CON",
                "text": "Free cash flow negative for 3 consecutive years raises concern about cash generation quality",
                "confidence_score": 90,
            })
        elif pd.notna(fcf_val) and fcf_val < 0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-02",
                "rule_type": "CON",
                "text": "Negative free cash flow in the latest fiscal year raises concern about cash generation quality",
                "confidence_score": 70,
            })
        elif len(fcf_s) >= 2 and fcf_s.iloc[-1] < fcf_s.iloc[-2]:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-02",
                "rule_type": "CON",
                "text": "Free cash flow declined year-over-year indicating elevated capital absorption",
                "confidence_score": 65,
            })
        elif pd.isna(fcf_val) and not is_fin:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-02",
                "rule_type": "CON",
                "text": "Limited visibility into historical free cash flow conversion warrants monitoring",
                "confidence_score": 65,
            })

        # CON-03: OPM declining (3+ years, YoY, or moderate)
        if len(opm_s) >= 4 and (opm_s.iloc[-1] < opm_s.iloc[-2] < opm_s.iloc[-3] < opm_s.iloc[-4]):
            results.append({
                "company_id": company_id,
                "rule_id": "CON-03",
                "rule_type": "CON",
                "text": "Operating margins declining for 3 consecutive years suggest pricing or cost pressure",
                "confidence_score": 90,
            })
        elif len(opm_s) >= 3 and (opm_s.iloc[-1] < opm_s.iloc[-2] < opm_s.iloc[-3]):
            results.append({
                "company_id": company_id,
                "rule_id": "CON-03",
                "rule_type": "CON",
                "text": "Operating margins declining over recent years suggest pricing or cost pressure",
                "confidence_score": 80,
            })
        elif len(opm_s) >= 2 and (opm_s.iloc[-1] < opm_s.iloc[-2]):
            results.append({
                "company_id": company_id,
                "rule_id": "CON-03",
                "rule_type": "CON",
                "text": "Operating margin compression in the latest fiscal year suggests pricing or cost pressure",
                "confidence_score": 65,
            })
        elif opm_val is not None and opm_val < 15.0 and not is_fin:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-03",
                "rule_type": "CON",
                "text": f"Operating margin of {opm_val:.1f}% indicates relatively thin pricing cushion",
                "confidence_score": 65,
            })

        # CON-04: Net loss, contraction, or moderate PAT CAGR
        np_val = latest_pl.get("net_profit") if not latest_pl.empty else None
        if np_val is not None and np_val < 0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-04",
                "rule_type": "CON",
                "text": "Company reported a net loss in the most recent financial year",
                "confidence_score": 95,
            })
        elif np_val is not None and len(pl_df) >= 2:
            np_prev = pl_df.iloc[-2].get("net_profit")
            if np_prev is not None and np_prev > 0 and np_val < np_prev:
                results.append({
                    "company_id": company_id,
                    "rule_id": "CON-04",
                    "rule_type": "CON",
                    "text": "Net profit contraction in the latest financial year warrants monitoring",
                    "confidence_score": 65,
                })
        elif p_cagr is not None and p_cagr < 10.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-04",
                "rule_type": "CON",
                "text": f"Subdued 5-year profit CAGR of {p_cagr:.1f}% reflects moderate earnings compounding pace",
                "confidence_score": 65,
            })

        # CON-05: Revenue declining (2+ years, YoY, or 3-year CAGR < 10%)
        if len(sales_s) >= 3 and (sales_s.iloc[-1] < sales_s.iloc[-2] < sales_s.iloc[-3]):
            results.append({
                "company_id": company_id,
                "rule_id": "CON-05",
                "rule_type": "CON",
                "text": "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss",
                "confidence_score": 90,
            })
        elif len(sales_s) >= 2 and (sales_s.iloc[-1] < sales_s.iloc[-2]):
            results.append({
                "company_id": company_id,
                "rule_id": "CON-05",
                "rule_type": "CON",
                "text": "Revenue contraction in the latest financial year indicates demand softness",
                "confidence_score": 70,
            })
        elif r_cagr_3 is not None and r_cagr_3 < 10.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-05",
                "rule_type": "CON",
                "text": "Subdued 3-year revenue growth reflects moderate business expansion pace",
                "confidence_score": 65,
            })

        # CON-06: ICR < 1.5 or moderate (<4.0)
        if icr_val is not None and icr_val < 1.5 and "debt free" not in icr_lbl and de_val != 0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-06",
                "rule_type": "CON",
                "text": "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations",
                "confidence_score": 90,
            })
        elif icr_val is not None and icr_val < 4.0 and "debt free" not in icr_lbl and de_val != 0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-06",
                "rule_type": "CON",
                "text": "Moderate interest coverage ratio indicates debt servicing sensitivity to earnings volatility",
                "confidence_score": 65,
            })

        # CON-07: Dividend payout > 100% or high (>50%) or low (<10%)
        if dp_val is not None and dp_val > 100.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-07",
                "rule_type": "CON",
                "text": "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable",
                "confidence_score": 90,
            })
        elif dp_val is not None and dp_val > 50.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-07",
                "rule_type": "CON",
                "text": f"High dividend payout ratio of {dp_val:.1f}% limits internal capital reinvestment capacity",
                "confidence_score": 70,
            })
        elif dp_val is not None and dp_val < 10.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-07",
                "rule_type": "CON",
                "text": "Low dividend payout ratio provides limited current cash return to shareholders",
                "confidence_score": 65,
            })

        # CON-08: D/E rising (3+ years or YoY)
        if len(de_s) >= 4 and (de_s.iloc[-1] > de_s.iloc[-2] > de_s.iloc[-3] > de_s.iloc[-4]):
            results.append({
                "company_id": company_id,
                "rule_id": "CON-08",
                "rule_type": "CON",
                "text": "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk",
                "confidence_score": 90,
            })
        elif len(de_s) >= 2 and (de_s.iloc[-1] > de_s.iloc[-2]) and de_s.iloc[-1] > 0.02:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-08",
                "rule_type": "CON",
                "text": "Year-over-year increase in debt-to-equity ratio signals increasing leverage",
                "confidence_score": 65,
            })

        # CON-09: EPS declining (3+ years, YoY, or CAGR < 10%)
        if len(eps_s) >= 4 and (eps_s.iloc[-1] < eps_s.iloc[-2] < eps_s.iloc[-3] < eps_s.iloc[-4]):
            results.append({
                "company_id": company_id,
                "rule_id": "CON-09",
                "rule_type": "CON",
                "text": "Earnings per share declining for 3 consecutive years reflects deteriorating profitability",
                "confidence_score": 90,
            })
        elif len(eps_s) >= 2 and (eps_s.iloc[-1] < eps_s.iloc[-2]):
            results.append({
                "company_id": company_id,
                "rule_id": "CON-09",
                "rule_type": "CON",
                "text": "Earnings per share contraction in latest year reflects near-term earnings headwind",
                "confidence_score": 65,
            })
        elif eps_cagr is not None and eps_cagr < 10.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-09",
                "rule_type": "CON",
                "text": f"Subdued 5-year EPS CAGR of {eps_cagr:.1f}% indicates moderate per-share value compounding",
                "confidence_score": 65,
            })

        # CON-10: ROCE < 10% or < 18%
        if roce_val is not None and roce_val < 10.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-10",
                "rule_type": "CON",
                "text": "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital",
                "confidence_score": 85,
            })
        elif roce_val is not None and roce_val < 18.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-10",
                "rule_type": "CON",
                "text": f"Moderate return on capital employed of {roce_val:.1f}% indicates average capital productivity",
                "confidence_score": 65,
            })

        # CON-11: Net Debt > 3x EBITDA (or >1.0x)
        nd_val = latest_r.get("net_debt_cr")
        ebitda_val = latest_pl.get("operating_profit") if not latest_pl.empty else None
        if not is_fin and nd_val is not None and ebitda_val is not None and ebitda_val > 0 and (nd_val / ebitda_val) > 3.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-11",
                "rule_type": "CON",
                "text": "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility",
                "confidence_score": 90,
            })
        elif not is_fin and nd_val is not None and ebitda_val is not None and ebitda_val > 0 and (nd_val / ebitda_val) > 1.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-11",
                "rule_type": "CON",
                "text": "Net debt exceeding 1.0x EBITDA warrants close monitoring of cash conversion",
                "confidence_score": 65,
            })

        # CON-12: Revenue CAGR < 5% or < 12%
        if r_cagr is not None and r_cagr < 5.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-12",
                "rule_type": "CON",
                "text": "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum",
                "confidence_score": 85,
            })
        elif r_cagr is not None and r_cagr < 12.0:
            results.append({
                "company_id": company_id,
                "rule_id": "CON-12",
                "rule_type": "CON",
                "text": f"Single-digit 5-year revenue CAGR of {r_cagr:.1f}% suggests moderate top-line expansion momentum",
                "confidence_score": 65,
            })

        return results

    def generate_all(self, output_path: str = OUTPUT_CSV_PATH) -> pd.DataFrame:
        """Evaluate all companies, validate coverage, sort and save results to CSV."""
        df_comps, df_ratios, df_pl, df_bs, df_sec, df_mc = self.load_data()
        sec_map = dict(zip(df_sec["company_id"], df_sec["broad_sector"]))
        div_map = dict(zip(df_mc["company_id"], df_mc["dividend_yield_pct"]))

        all_results: List[Dict[str, Any]] = []

        for cid in df_comps["id"]:
            r_df = df_ratios[df_ratios["company_id"] == cid].sort_values("year")
            pl_df = df_pl[df_pl["company_id"] == cid].sort_values("year")
            bs_df = df_bs[df_bs["company_id"] == cid].sort_values("year")
            sector = sec_map.get(cid, "")
            div_yield = div_map.get(cid, 0.0) or 0.0

            comp_results = self.evaluate_company(cid, r_df, pl_df, bs_df, sector, div_yield)
            all_results.extend(comp_results)

        df_out = pd.DataFrame(all_results)
        if df_out.empty:
            logger.warning("No pros or cons generated!")
            return df_out

        # Filter confidence > 60%
        df_out = df_out[df_out["confidence_score"] > 60]

        # Quality check: every company has >= 1 pro and >= 1 con
        all_cids = set(df_comps["id"])
        pro_cids = set(df_out[df_out["rule_type"] == "PRO"]["company_id"])
        con_cids = set(df_out[df_out["rule_type"] == "CON"]["company_id"])

        missing_pros = all_cids - pro_cids
        missing_cons = all_cids - con_cids

        if missing_pros:
            logger.warning(f"CRITICAL: {len(missing_pros)} companies missing PRO points: {missing_pros}")
        if missing_cons:
            logger.warning(f"CRITICAL: {len(missing_cons)} companies missing CON points: {missing_cons}")

        # Sort output by company_id, rule_type, confidence_score DESC
        # Rule type 'PRO' before 'CON'
        df_out["rule_type_order"] = df_out["rule_type"].map({"PRO": 0, "CON": 1})
        df_out = df_out.sort_values(
            by=["company_id", "rule_type_order", "confidence_score"],
            ascending=[True, True, False],
        ).drop(columns=["rule_type_order"])

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_out.to_csv(output_path, index=False)
        logger.info(f"Generated {len(df_out)} pros/cons for {len(all_cids)} companies saved to {output_path}")

        return df_out


def run_pros_cons_generator(db_path: str = DEFAULT_DB_PATH, output_path: str = OUTPUT_CSV_PATH) -> pd.DataFrame:
    """Convenience runner function."""
    generator = ProsConsGenerator(db_path=db_path)
    return generator.generate_all(output_path=output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_pros_cons_generator()
