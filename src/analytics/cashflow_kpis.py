"""Cash Flow KPIs & Capital Allocation Engine.

Implements Free Cash Flow, CapEx Intensity, FCF Conversion,
5-year CFO Quality Score, 8-Pattern Capital Allocation Classifier,
Distress Signal Detection, Deleveraging Tracking, and Multi-period Dynamics.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(root_dir, "data", "nifty100.db")
if not os.path.exists(DEFAULT_DB_PATH) and os.path.exists(os.path.join(root_dir, "nifty100.db")):
    DEFAULT_DB_PATH = os.path.join(root_dir, "nifty100.db")

# Pattern Labels
PATTERN_REINVESTOR = "Reinvestor"
PATTERN_SHAREHOLDER_RETURNS = "Shareholder Returns"
PATTERN_LIQUIDATING_ASSETS = "Liquidating Assets"
PATTERN_DISTRESS_SIGNAL = "Distress Signal"
PATTERN_GROWTH_FUNDED_DEBT = "Growth Funded by Debt"
PATTERN_CASH_ACCUMULATOR = "Cash Accumulator"
PATTERN_PRE_REVENUE_BURN = "Pre-Revenue / Cash Burn"
PATTERN_GROWTH_MIXED = "Growth / Mixed"
PATTERN_RESTRUCTURING = "Restructuring"


def calculate_free_cash_flow(
    operating_activity: Optional[float], investing_activity: Optional[float]
) -> Optional[float]:
    """Calculate Free Cash Flow: CFO + CFI.
    
    Since CFI is typically negative (cash outflow for capex/investments),
    CFO + CFI represents net cash remaining after investments.
    """
    if operating_activity is None or investing_activity is None:
        return None
    return round(float(operating_activity + investing_activity), 2)


def calculate_capex_intensity(
    investing_activity: Optional[float], sales: Optional[float]
) -> Tuple[Optional[float], str]:
    """Calculate CapEx Intensity percentage: abs(investing_activity) / sales * 100.
    
    Classification:
    - < 3%: 'Asset Light'
    - 3% - 8%: 'Moderate'
    - > 8%: 'Capital Intensive'
    
    Returns:
        (intensity_percentage, category_label)
    """
    if sales is None or investing_activity is None or sales <= 0:
        return (None, "N/A")
    intensity = round((abs(float(investing_activity)) / float(sales)) * 100, 2)
    if intensity < 3.0:
        label = "Asset Light"
    elif intensity <= 8.0:
        label = "Moderate"
    else:
        label = "Capital Intensive"
    return (intensity, label)


def calculate_fcf_conversion(
    fcf: Optional[float], operating_profit: Optional[float]
) -> Tuple[Optional[float], str]:
    """Calculate FCF Conversion Rate: (FCF / operating_profit) * 100.
    
    Tiers:
    - > 60%: 'Efficient'
    - 30% - 60%: 'Moderate'
    - < 30%: 'CapEx Heavy'
    
    Returns:
        (conversion_percentage, tier_label)
    """
    if fcf is None or operating_profit is None or operating_profit == 0:
        return (None, "N/A")
    conversion = round((float(fcf) / float(operating_profit)) * 100, 2)
    if conversion > 60.0:
        tier = "Efficient"
    elif conversion >= 30.0:
        tier = "Moderate"
    else:
        tier = "CapEx Heavy"
    return (conversion, tier)


def calculate_cfo_quality_score(
    cfo_series: List[Optional[float]], pat_series: List[Optional[float]]
) -> Tuple[Optional[float], str]:
    """Calculate 5-Year CFO Quality Score: ratio and classification.
    
    Rules:
    - High Quality: CFO > Net Profit for 4+ out of 5 years (cfo_net_profit_ratio >= 1.0)
    - Moderate Quality: CFO > Net Profit for 2-3 out of 5 years
    - Accrual Risk: CFO < Net Profit for 4+ out of 5 years
    """
    cfo_gt_pat = 0
    valid_years = 0
    ratios: List[float] = []

    for cfo, pat in zip(cfo_series, pat_series):
        if cfo is not None and pat is not None and pat > 0:
            ratios.append(float(cfo) / float(pat))
            valid_years += 1
            if float(cfo) > float(pat):
                cfo_gt_pat += 1
        elif cfo is not None and pat is not None:
            valid_years += 1
            if float(cfo) > float(pat):
                cfo_gt_pat += 1

    if valid_years == 0:
        return (None, "N/A")

    avg_ratio = round(sum(ratios) / len(ratios), 2) if ratios else None

    if valid_years >= 4:
        if cfo_gt_pat >= 4:
            label = "High Quality Earnings"
        elif cfo_gt_pat in [2, 3]:
            label = "Moderate Quality"
        else:
            label = "Accrual Risk"
    else:
        prop = cfo_gt_pat / valid_years
        if prop >= 0.75:
            label = "High Quality Earnings"
        elif prop >= 0.4:
            label = "Moderate Quality"
        else:
            label = "Accrual Risk"

    return (avg_ratio, label)


def classify_capital_allocation(
    cfo: Optional[float],
    cfi: Optional[float],
    cff: Optional[float],
    cfo_to_pat: Optional[float] = None,
) -> Tuple[str, str, str, str]:
    """Classify Capital Allocation into one of the 8 canonical lifecycle patterns.
    
    Args:
        cfo: Cash Flow from Operating Activities
        cfi: Cash Flow from Investing Activities
        cff: Cash Flow from Financing Activities
        cfo_to_pat: Optional CFO/PAT ratio to distinguish Reinvestor vs Shareholder Returns

    Returns:
        (cfo_sign, cfi_sign, cff_sign, pattern_label)
    """
    if cfo is None or cfi is None or cff is None:
        return ("?", "?", "?", "Insufficient Data")

    cfo_sign = "+" if cfo >= 0 else "-"
    cfi_sign = "+" if cfi >= 0 else "-"
    cff_sign = "+" if cff >= 0 else "-"

    sign_pattern = (cfo_sign, cfi_sign, cff_sign)

    if sign_pattern == ("+", "-", "-"):
        if cfo_to_pat is not None and cfo_to_pat > 1.0:
            pattern = PATTERN_SHAREHOLDER_RETURNS
        else:
            pattern = PATTERN_REINVESTOR
    elif sign_pattern == ("+", "+", "-"):
        pattern = PATTERN_LIQUIDATING_ASSETS
    elif sign_pattern == ("-", "+", "+"):
        pattern = PATTERN_DISTRESS_SIGNAL
    elif sign_pattern == ("-", "-", "+"):
        pattern = PATTERN_GROWTH_FUNDED_DEBT
    elif sign_pattern == ("+", "+", "+"):
        pattern = PATTERN_CASH_ACCUMULATOR
    elif sign_pattern == ("-", "-", "-"):
        pattern = PATTERN_PRE_REVENUE_BURN
    elif sign_pattern == ("+", "-", "+"):
        pattern = PATTERN_GROWTH_MIXED
    elif sign_pattern == ("-", "+", "-"):
        pattern = PATTERN_RESTRUCTURING
    else:
        pattern = "Mixed / Other"

    return (cfo_sign, cfi_sign, cff_sign, pattern)


def determine_pattern_change_type(p_2023: str, p_2024: str) -> str:
    """Classify transition between capital allocation patterns into economic themes."""
    if p_2024 in [PATTERN_DISTRESS_SIGNAL, PATTERN_PRE_REVENUE_BURN, PATTERN_RESTRUCTURING]:
        return "Distress"
    if p_2024 in [PATTERN_GROWTH_MIXED, PATTERN_GROWTH_FUNDED_DEBT, PATTERN_REINVESTOR]:
        return "Expansion"
    if p_2024 in [PATTERN_SHAREHOLDER_RETURNS]:
        return "Deleveraging"
    if p_2024 in [PATTERN_LIQUIDATING_ASSETS, PATTERN_CASH_ACCUMULATOR]:
        return "Contraction"
    return "Deleveraging"


class CashFlowIntelligenceEngine:
    """Computes Cash Flow Intelligence, multi-period pattern dynamics, and generates outputs."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def load_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Load datasets from SQLite database."""
        conn = sqlite3.connect(self.db_path)
        try:
            df_comps = pd.read_sql("SELECT id, company_name FROM companies ORDER BY id", conn)
            df_cf = pd.read_sql("SELECT * FROM cashflow WHERE year != 'TTM' ORDER BY company_id, year", conn)
            df_pl = pd.read_sql(
                "SELECT company_id, year, sales, operating_profit, net_profit FROM profitandloss WHERE year != 'TTM' ORDER BY company_id, year",
                conn,
            )
            df_bs = pd.read_sql(
                "SELECT company_id, year, borrowings FROM balancesheet WHERE year != 'TTM' ORDER BY company_id, year",
                conn,
            )
            df_sec = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
        finally:
            conn.close()
        return df_comps, df_cf, df_pl, df_bs, df_sec

    def run_analysis(
        self,
        output_excel: str = os.path.join(root_dir, "output", "cashflow_intelligence.xlsx"),
        distress_csv: str = os.path.join(root_dir, "output", "distress_alerts.csv"),
        pattern_csv: str = os.path.join(root_dir, "output", "pattern_changes.csv"),
    ) -> Dict[str, pd.DataFrame]:
        """Run full Cash Flow Intelligence pipeline and write all output files."""
        df_comps, df_cf, df_pl, df_bs, df_sec = self.load_data()
        sec_map = dict(zip(df_sec["company_id"], df_sec["broad_sector"]))

        records: List[Dict[str, Any]] = []
        distress_records: List[Dict[str, Any]] = []
        pattern_changes: List[Dict[str, Any]] = []

        for _, comp in df_comps.iterrows():
            cid = comp["id"]
            cname = comp["company_name"]
            sector = sec_map.get(cid, "N/A")

            sub_cf = df_cf[df_cf["company_id"] == cid].sort_values("year")
            sub_pl = df_pl[df_pl["company_id"] == cid].sort_values("year")
            sub_bs = df_bs[df_bs["company_id"] == cid].sort_values("year")

            if sub_cf.empty:
                records.append({
                    "company_id": cid,
                    "company_name": cname,
                    "sector": sector,
                    "cfo_quality_score": "N/A",
                    "capex_intensity_label": "N/A",
                    "capital_allocation_pattern": "Insufficient Data",
                    "avg_cfo_cr": None,
                    "avg_capex_cr": None,
                    "avg_fcf_cr": None,
                    "distress_signal": False,
                    "deleveraging_flag": False,
                })
                continue

            # Merge annual statement records
            m = pd.merge(sub_cf, sub_pl, on=["company_id", "year"], how="left")
            m = pd.merge(m, sub_bs, on=["company_id", "year"], how="left")

            last_5 = m.tail(5)

            # 1. 5-year CFO Quality Score
            cfo_list = last_5["operating_activity"].tolist()
            pat_list = last_5["net_profit"].tolist()
            _, cfo_quality_label = calculate_cfo_quality_score(cfo_list, pat_list)

            # 2. CapEx Intensity
            latest_row = m.iloc[-1]
            cfi = latest_row.get("investing_activity")
            sales = latest_row.get("sales")
            _, capex_intensity_label = calculate_capex_intensity(cfi, sales)

            # 3. Capital Allocation Pattern (latest)
            cfo_latest = latest_row.get("operating_activity")
            cfi_latest = latest_row.get("investing_activity")
            cff_latest = latest_row.get("financing_activity")
            pat_latest = latest_row.get("net_profit")
            cfo_to_pat = (
                float(cfo_latest) / float(pat_latest)
                if pd.notna(cfo_latest) and pd.notna(pat_latest) and pat_latest > 0
                else None
            )
            _, _, _, alloc_pattern = classify_capital_allocation(cfo_latest, cfi_latest, cff_latest, cfo_to_pat)

            # 4. 5-year averages
            cfo_clean = last_5["operating_activity"].dropna()
            avg_cfo = round(float(cfo_clean.mean()), 2) if not cfo_clean.empty else None

            cfi_clean = last_5["investing_activity"].dropna().abs()
            avg_capex = round(float(cfi_clean.mean()), 2) if not cfi_clean.empty else None

            fcf_series = last_5.apply(
                lambda r: calculate_free_cash_flow(r["operating_activity"], r["investing_activity"]), axis=1
            ).dropna()
            avg_fcf = round(float(fcf_series.mean()), 2) if not fcf_series.empty else None

            # 5. Distress signal (latest)
            distress = bool(
                pd.notna(cfo_latest) and pd.notna(cff_latest) and cfo_latest < 0 and cff_latest > 0
            )

            # 6. Deleveraging flag (latest)
            deleveraging = False
            if pd.notna(cff_latest) and cff_latest < 0 and len(m) >= 2:
                b_curr = latest_row.get("borrowings")
                b_prev = m.iloc[-2].get("borrowings")
                if pd.notna(b_curr) and pd.notna(b_prev) and b_curr < b_prev:
                    deleveraging = True

            records.append({
                "company_id": cid,
                "company_name": cname,
                "sector": sector,
                "cfo_quality_score": cfo_quality_label,
                "capex_intensity_label": capex_intensity_label,
                "capital_allocation_pattern": alloc_pattern,
                "avg_cfo_cr": avg_cfo,
                "avg_capex_cr": avg_capex,
                "avg_fcf_cr": avg_fcf,
                "distress_signal": distress,
                "deleveraging_flag": deleveraging,
            })

            # Check 3-year historical distress signals
            for _, row in m.tail(3).iterrows():
                c = row.get("operating_activity")
                f = row.get("financing_activity")
                if pd.notna(c) and pd.notna(f) and c < 0 and f > 0:
                    distress_records.append({
                        "company_id": cid,
                        "year": row["year"],
                        "cfo": c,
                        "cff": f,
                        "distress_flag": True,
                        "description": (
                            f"Operating cash flow is negative ({c:.1f} Cr) while financing cash flow "
                            f"is positive ({f:.1f} Cr), indicating debt/equity reliance to fund operations."
                        ),
                    })

            # Capital allocation pattern changes between 2023 and 2024
            row_2023 = m[m["year"].str.startswith("2023")]
            row_2024 = m[m["year"].str.startswith("2024")]
            if not row_2023.empty and not row_2024.empty:
                r23 = row_2023.iloc[-1]
                r24 = row_2024.iloc[-1]
                c23, i23, f23, p23 = (
                    r23["operating_activity"],
                    r23["investing_activity"],
                    r23["financing_activity"],
                    r23["net_profit"],
                )
                c24, i24, f24, p24 = (
                    r24["operating_activity"],
                    r24["investing_activity"],
                    r24["financing_activity"],
                    r24["net_profit"],
                )

                c23_p = float(c23) / float(p23) if pd.notna(c23) and pd.notna(p23) and p23 > 0 else None
                c24_p = float(c24) / float(p24) if pd.notna(c24) and pd.notna(p24) and p24 > 0 else None

                _, _, _, p_2023 = classify_capital_allocation(c23, i23, f23, c23_p)
                _, _, _, p_2024 = classify_capital_allocation(c24, i24, f24, c24_p)

                if (
                    p_2023 != p_2024
                    and p_2023 != "Insufficient Data"
                    and p_2024 != "Insufficient Data"
                ):
                    chg_type = determine_pattern_change_type(p_2023, p_2024)
                    pattern_changes.append({
                        "company_id": cid,
                        "pattern_2023": p_2023,
                        "pattern_2024": p_2024,
                        "change_type": chg_type,
                    })

        df_intel = pd.DataFrame(records)
        df_distress = pd.DataFrame(distress_records)
        df_changes = pd.DataFrame(pattern_changes)

        # Write output files
        os.makedirs(os.path.dirname(output_excel), exist_ok=True)
        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
            df_intel.to_excel(writer, sheet_name="CashFlow_Intelligence", index=False)
        logger.info(f"Saved {len(df_intel)} company cashflow intelligence records to {output_excel}")

        df_distress.to_csv(distress_csv, index=False)
        logger.info(f"Saved {len(df_distress)} distress alert records to {distress_csv}")

        df_changes.to_csv(pattern_csv, index=False)
        logger.info(f"Saved {len(df_changes)} pattern change records to {pattern_csv}")

        return {
            "intelligence": df_intel,
            "distress_alerts": df_distress,
            "pattern_changes": df_changes,
        }


def run_cashflow_intelligence() -> Dict[str, pd.DataFrame]:
    """Convenience runner."""
    engine = CashFlowIntelligenceEngine()
    return engine.run_analysis()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_cashflow_intelligence()
