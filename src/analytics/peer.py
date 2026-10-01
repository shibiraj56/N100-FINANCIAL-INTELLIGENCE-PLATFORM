"""Peer Comparison & Intra-Group Percentile Ranking Engine.

Computes intra-peer percentile rankings across 10 key metrics for all 11 peer groups,
populates SQLite peer_percentiles table, generates polar radar charts with peer group overlays,
and creates the multi-sheet styled output/peer_comparison.xlsx report with gold benchmark highlighting.
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
import pandas as pd
from scipy.stats import rankdata

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(root_dir, "data", "nifty100.db")

# 10 Standard Ranking Metrics: (metric_id, display_name, raw_column, is_inverse)
RANK_METRICS = [
    ("roe", "ROE", "return_on_equity_pct", False),
    ("roce", "ROCE", "roce_pct", False),
    ("npm", "Net Profit Margin", "net_profit_margin_pct", False),
    ("de", "Debt-to-Equity", "debt_to_equity", True),  # Lower is better!
    ("fcf", "Free Cash Flow", "free_cash_flow_cr", False),
    ("pat_cagr_5yr", "5Y PAT CAGR", "pat_cagr_5yr", False),
    ("rev_cagr_5yr", "5Y Revenue CAGR", "revenue_cagr_5yr", False),
    ("eps_cagr_5yr", "5Y EPS CAGR", "eps_cagr_5yr", False),
    ("icr", "Interest Coverage", "interest_coverage", False),
    ("asset_turnover", "Asset Turnover", "asset_turnover", False),
]

# 8 Axes for Polar Radar Charts: (axis_label, raw_column, is_inverse, default_max)
RADAR_AXES = [
    ("ROE", "return_on_equity_pct", False, 35.0),
    ("ROCE", "roce_pct", False, 35.0),
    ("NPM", "net_profit_margin_pct", False, 30.0),
    ("D/E Score", "debt_to_equity", True, 2.0),
    ("FCF Score", "free_cash_flow_cr", False, 5000.0),
    ("PAT CAGR 5Y", "pat_cagr_5yr", False, 30.0),
    ("Rev CAGR 5Y", "revenue_cagr_5yr", False, 25.0),
    ("Quality Score", "composite_quality_score", False, 100.0),
]

# Styling constants for Excel
HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
BENCHMARK_FILL = PatternFill(start_color="FFE599", end_color="FFE599", fill_type="solid")
BENCHMARK_FONT = Font(name="Calibri", size=10, bold=True, color="7F6000")
MEDIAN_FILL = PatternFill(start_color="EAEAEA", end_color="EAEAEA", fill_type="solid")
MEDIAN_FONT = Font(name="Calibri", size=10, bold=True, italic=True)
GREEN_FILL = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid")
GREEN_FONT = Font(name="Calibri", size=9, color="274E13")
YELLOW_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
YELLOW_FONT = Font(name="Calibri", size=9, color="7F6000")
RED_FILL = PatternFill(start_color="F4CCCC", end_color="F4CCCC", fill_type="solid")
RED_FONT = Font(name="Calibri", size=9, color="990000")
DATA_FONT = Font(name="Calibri", size=9)

THIN_BORDER = Border(
    left=Side(style="thin", color="D3D3D3"),
    right=Side(style="thin", color="D3D3D3"),
    top=Side(style="thin", color="D3D3D3"),
    bottom=Side(style="thin", color="D3D3D3"),
)


def compute_percent_rank(values: List[Optional[float]], is_inverse: bool = False) -> List[float]:
    """Compute SQL-equivalent PERCENT_RANK for a list of values.

    Formula: (rank - 1) / (N - 1) where rank is 1-indexed.
    For is_inverse=True, lower values receive higher ranks (1.0 - rank).
    """
    clean_vals = [float(v) if v is not None and not pd.isna(v) else -1e9 for v in values]
    n = len(clean_vals)
    if n <= 1:
        return [1.0] * n

    # rankdata: lowest gets rank 1, highest gets rank N
    ranks = rankdata(clean_vals, method="average")
    pct_ranks = (ranks - 1.0) / (n - 1.0)

    if is_inverse:
        # Invert: lowest value gets 1.0, highest gets 0.0
        # If value was placeholder -1e9 (missing), assign 0.0
        result = []
        for orig, r in zip(values, pct_ranks):
            if orig is None or pd.isna(orig):
                result.append(0.0)
            else:
                result.append(round(1.0 - r, 4))
        return result
    else:
        result = []
        for orig, r in zip(values, pct_ranks):
            if orig is None or pd.isna(orig):
                result.append(0.0)
            else:
                result.append(round(r, 4))
        return result


class PeerEngine:
    """Intra-group peer percentile ranking, radar chart generator, and comparison reporting."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def load_peer_universe(self, year: str = "2024-03") -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load peer group mappings and unified financial ratios dataset."""
        conn = sqlite3.connect(self.db_path)
        df_pg = pd.read_sql("SELECT * FROM peer_groups", conn)
        query = """
        SELECT 
            r.company_id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            r.year,
            r.return_on_equity_pct,
            r.roce_pct,
            r.net_profit_margin_pct,
            r.operating_profit_margin_pct,
            r.debt_to_equity,
            r.interest_coverage,
            r.icr_label,
            r.free_cash_flow_cr,
            r.pat_cagr_5yr,
            r.revenue_cagr_5yr,
            r.eps_cagr_5yr,
            r.asset_turnover,
            r.composite_quality_score,
            mc.pe_ratio,
            mc.pb_ratio,
            mc.dividend_yield_pct,
            pl.sales,
            pl.net_profit
        FROM financial_ratios r
        JOIN companies c ON r.company_id = c.id
        LEFT JOIN sectors s ON r.company_id = s.company_id
        LEFT JOIN market_cap mc ON r.company_id = mc.company_id AND r.year = mc.year
        LEFT JOIN profitandloss pl ON r.company_id = pl.company_id AND r.year = pl.year
        WHERE r.year = ?
        """
        df_ratios = pd.read_sql(query, conn, params=(year,))
        conn.close()
        return df_pg, df_ratios

    def compute_peer_percentiles(self, year: str = "2024-03") -> pd.DataFrame:
        """Compute intra-group percentile rankings for all 10 metrics across all 11 peer groups.

        Populates peer_percentiles table in SQLite and mirrors to nifty100.db.
        """
        df_pg, df_ratios = self.load_peer_universe(year=year)
        merged = pd.merge(df_pg, df_ratios, on="company_id", how="inner")

        records: List[Dict[str, Any]] = []

        for group_name, group_df in merged.groupby("peer_group_name"):
            group_records = group_df.to_dict("records")
            cids = [r["company_id"] for r in group_records]

            for metric_id, disp_name, raw_col, is_inverse in RANK_METRICS:
                raw_values = []
                for r in group_records:
                    val = r.get(raw_col)
                    # For ICR, if debt-free, assign high substitute 999.0
                    if raw_col == "interest_coverage":
                        label = str(r.get("icr_label", "")).lower()
                        if "debt free" in label or r.get("debt_to_equity") == 0:
                            val = 999.0
                    raw_values.append(val)

                pct_ranks = compute_percent_rank(raw_values, is_inverse=is_inverse)

                for cid, val, pr in zip(cids, raw_values, pct_ranks):
                    records.append(
                        {
                            "company_id": cid,
                            "peer_group_name": group_name,
                            "metric": metric_id,
                            "value": None if val == 999.0 and raw_col == "interest_coverage" else val,
                            "percentile_rank": pr,
                            "year": year,
                        }
                    )

        df_percentiles = pd.DataFrame(records)

        # Write to SQLite
        conn = sqlite3.connect(self.db_path)
        conn.execute("DROP TABLE IF EXISTS peer_percentiles;")
        conn.execute(
            """
            CREATE TABLE peer_percentiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT NOT NULL,
                peer_group_name TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                percentile_rank REAL,
                year TEXT NOT NULL
            );
            """
        )
        df_percentiles.to_sql("peer_percentiles", conn, if_exists="append", index=False)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pp_comp ON peer_percentiles(company_id, peer_group_name);")
        conn.commit()
        conn.close()

        # Mirror to root nifty100.db
        root_db = os.path.join(root_dir, "nifty100.db")
        if os.path.exists(self.db_path) and os.path.abspath(self.db_path) != os.path.abspath(root_db):
            shutil.copyfile(self.db_path, root_db)

        logger.info("Successfully populated peer_percentiles table with %d records", len(df_percentiles))
        return df_percentiles

    def get_company_percentiles(self, company_id: str, year: str = "2024-03") -> Union[pd.DataFrame, Dict[str, str]]:
        """Retrieve percentile rankings for a company, or return friendly unassigned message."""
        conn = sqlite3.connect(self.db_path)
        query = "SELECT * FROM peer_percentiles WHERE company_id = ? AND year = ?"
        df = pd.read_sql(query, conn, params=(company_id, year))
        conn.close()
        if df.empty:
            return {"message": "No peer group assigned", "company_id": company_id}
        return df

    def generate_radar_chart(
        self,
        company_id: str,
        df_pg: pd.DataFrame,
        df_ratios: pd.DataFrame,
        output_dir: str = "reports/radar_charts",
    ) -> str:
        """Generate an 8-axis polar radar chart for a company with peer group overlay.

        For companies with no peer group, overlays against Nifty 100 universe average.
        """
        os.makedirs(output_dir, exist_ok=True)
        comp_match = df_ratios[df_ratios["company_id"] == company_id]
        if comp_match.empty:
            return ""
        comp_row = comp_match.iloc[0]
        comp_name = comp_row.get("company_name", company_id)

        # Find peer group
        pg_match = df_pg[df_pg["company_id"] == company_id]
        has_peer = not pg_match.empty
        peer_name = pg_match.iloc[0]["peer_group_name"] if has_peer else "Nifty 100 Universe"

        # Compare universe
        if has_peer:
            peer_cids = df_pg[df_pg["peer_group_name"] == peer_name]["company_id"].tolist()
            bench_df = df_ratios[df_ratios["company_id"].isin(peer_cids)]
        else:
            bench_df = df_ratios

        # Normalize 8 axes to 0-100 scale
        categories = [axis[0] for axis in RADAR_AXES]
        comp_values = []
        peer_values = []

        for _, raw_col, is_inv, def_max in RADAR_AXES:
            c_val = comp_row.get(raw_col)
            p_val = bench_df[raw_col].median()

            # Clean and scale
            def scale_val(v: Any) -> float:
                if v is None or pd.isna(v):
                    return 0.0
                try:
                    vf = float(v)
                except (ValueError, TypeError):
                    return 0.0
                if is_inv:
                    # For D/E: 0 -> 100, 2.0 -> 0
                    return max(0.0, min(100.0, 100.0 - (vf / def_max * 100.0)))
                else:
                    return max(0.0, min(100.0, (vf / def_max) * 100.0))

            comp_values.append(scale_val(c_val))
            peer_values.append(scale_val(p_val))

        # Close the polar loop
        n_vars = len(categories)
        angles = [n / float(n_vars) * 2 * math.pi for n in range(n_vars)]
        angles += angles[:1]
        comp_values += comp_values[:1]
        peer_values += peer_values[:1]

        fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw=dict(polar=True))
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)

        # Draw axis category labels
        plt.xticks(angles[:-1], categories, size=9, weight="bold", color="#1F4E79")
        ax.set_rlabel_position(0)
        plt.yticks([25, 50, 75, 100], ["25", "50", "75", "100"], color="#7F7F7F", size=8)
        plt.ylim(0, 100)

        # Plot Peer/Universe Median
        bench_label = f"{peer_name} Median" if has_peer else "N100 Universe Median"
        ax.plot(angles, peer_values, linewidth=1.8, linestyle="dashed", color="#E67E22", label=bench_label)
        ax.fill(angles, peer_values, color="#E67E22", alpha=0.08)

        # Plot Company values
        ax.plot(angles, comp_values, linewidth=2.2, color="#008080", label=f"{company_id} ({comp_name[:18]})")
        ax.fill(angles, comp_values, color="#008080", alpha=0.25)

        # Title & Legend
        plt.title(f"{company_id} — Financial Performance Radar\nPeer Group: {peer_name}", size=11, weight="bold", pad=20)
        plt.legend(loc="upper right", bbox_to_anchor=(1.25, 1.1), fontsize=8)

        plt.tight_layout()
        out_path = os.path.join(output_dir, f"{company_id}_radar.png")
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        return out_path

    def generate_all_radar_charts(self, year: str = "2024-03", output_dir: str = "reports/radar_charts") -> int:
        """Generate radar charts for all 92 companies."""
        os.makedirs(output_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        all_companies = [r[0] for r in conn.execute("SELECT id FROM companies ORDER BY id").fetchall()]
        conn.close()

        df_pg, df_ratios = self.load_peer_universe(year=year)
        count = 0
        for cid in all_companies:
            if cid in df_ratios["company_id"].values:
                self.generate_radar_chart(cid, df_pg, df_ratios, output_dir=output_dir)
                count += 1
            else:
                # Load latest ratios for non-March year endings (e.g. SIEMENS September)
                conn = sqlite3.connect(self.db_path)
                df_single = pd.read_sql(f"""
                    SELECT r.company_id, c.company_name, s.broad_sector, s.sub_sector, r.year,
                           r.return_on_equity_pct, r.roce_pct, r.net_profit_margin_pct, r.operating_profit_margin_pct,
                           r.debt_to_equity, r.interest_coverage, r.icr_label, r.free_cash_flow_cr,
                           r.pat_cagr_5yr, r.revenue_cagr_5yr, r.eps_cagr_5yr, r.asset_turnover,
                           r.composite_quality_score, mc.pe_ratio, mc.pb_ratio, mc.dividend_yield_pct,
                           pl.sales, pl.net_profit
                    FROM financial_ratios r
                    JOIN companies c ON r.company_id = c.id
                    LEFT JOIN sectors s ON r.company_id = s.company_id
                    LEFT JOIN market_cap mc ON r.company_id = mc.company_id AND r.year = mc.year
                    LEFT JOIN profitandloss pl ON r.company_id = pl.company_id AND r.year = pl.year
                    WHERE r.company_id = '{cid}'
                    ORDER BY r.year DESC LIMIT 1
                """, conn)
                conn.close()
                if not df_single.empty:
                    combined_ratios = pd.concat([df_ratios, df_single], ignore_index=True)
                    self.generate_radar_chart(cid, df_pg, combined_ratios, output_dir=output_dir)
                    count += 1

        logger.info("Generated %d radar charts in %s", count, output_dir)
        return count

    def export_peer_comparison_workbook(
        self, year: str = "2024-03", output_path: str = "output/peer_comparison.xlsx"
    ) -> str:
        """Create output/peer_comparison.xlsx containing 11 styled sheets, one per peer group."""
        df_pg, df_ratios = self.load_peer_universe(year=year)
        self.compute_peer_percentiles(year=year)

        conn = sqlite3.connect(self.db_path)
        df_pp = pd.read_sql("SELECT * FROM peer_percentiles WHERE year = ?", conn, params=(year,))
        conn.close()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        merged = pd.merge(df_pg, df_ratios, on="company_id", how="inner")

        # 20 displayed columns:
        col_specs = [
            ("company_id", "Ticker", False),
            ("company_name", "Company Name", False),
            ("is_benchmark", "Benchmark?", False),
            ("composite_quality_score", "Quality Score", False),
            ("return_on_equity_pct", "ROE (%)", True),
            ("roce_pct", "ROCE (%)", True),
            ("net_profit_margin_pct", "NPM (%)", True),
            ("operating_profit_margin_pct", "OPM (%)", False),
            ("debt_to_equity", "D/E", True),
            ("interest_coverage", "ICR", True),
            ("free_cash_flow_cr", "FCF (₹ Cr)", True),
            ("pat_cagr_5yr", "5Y PAT CAGR (%)", True),
            ("revenue_cagr_5yr", "5Y Rev CAGR (%)", True),
            ("eps_cagr_5yr", "5Y EPS CAGR (%)", True),
            ("asset_turnover", "Asset Turnover", True),
            ("sales", "Revenue (₹ Cr)", False),
            ("net_profit", "Net Profit (₹ Cr)", False),
            ("pe_ratio", "P/E", False),
            ("pb_ratio", "P/B", False),
            ("dividend_yield_pct", "Div Yield (%)", False),
        ]

        # Metric ID mapping
        col_to_metric = {
            "return_on_equity_pct": "roe",
            "roce_pct": "roce",
            "net_profit_margin_pct": "npm",
            "debt_to_equity": "de",
            "free_cash_flow_cr": "fcf",
            "pat_cagr_5yr": "pat_cagr_5yr",
            "revenue_cagr_5yr": "rev_cagr_5yr",
            "eps_cagr_5yr": "eps_cagr_5yr",
            "interest_coverage": "icr",
            "asset_turnover": "asset_turnover",
        }

        for group_name, group_df in merged.groupby("peer_group_name"):
            sheet_title = group_name[:31].replace("/", "-")
            ws = wb.create_sheet(title=sheet_title)
            ws.views.sheetView[0].showGridLines = True

            # Headers
            headers = [disp for _, disp, _ in col_specs]
            ws.append(headers)
            for c_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=c_idx)
                cell.fill = HEADER_FILL
                cell.font = HEADER_FONT
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = THIN_BORDER
            ws.row_dimensions[1].height = 25

            # Data rows
            for r_idx, (_, row_data) in enumerate(group_df.iterrows(), start=2):
                cid = row_data["company_id"]
                is_bench = bool(row_data.get("is_benchmark") == 1)

                for c_idx, (raw_col, _, has_rank) in enumerate(col_specs, start=1):
                    val = row_data.get(raw_col)

                    if raw_col == "is_benchmark":
                        cell_val = "★ Benchmark" if is_bench else "Peer"
                    elif isinstance(val, (float, int)):
                        cell_val = round(val, 2)
                    elif pd.isna(val):
                        cell_val = "—"
                    else:
                        cell_val = str(val)

                    cell = ws.cell(row=r_idx, column=c_idx, value=cell_val)
                    cell.font = DATA_FONT
                    cell.border = THIN_BORDER

                    # Alignments
                    if c_idx in (1, 3):
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    elif c_idx == 2:
                        cell.alignment = Alignment(horizontal="left", vertical="center")
                    else:
                        cell.alignment = Alignment(horizontal="right", vertical="center")

                    # Highlight benchmark row
                    if is_bench and not has_rank:
                        cell.fill = BENCHMARK_FILL
                        cell.font = BENCHMARK_FONT

                    # Percentile cell color-coding
                    if has_rank and raw_col in col_to_metric:
                        m_id = col_to_metric[raw_col]
                        rank_sub = df_pp[(df_pp["company_id"] == cid) & (df_pp["metric"] == m_id)]
                        if not rank_sub.empty:
                            p_rank = rank_sub.iloc[0]["percentile_rank"]
                            if p_rank >= 0.75:
                                cell.fill = GREEN_FILL
                                cell.font = GREEN_FONT
                            elif p_rank >= 0.25:
                                cell.fill = YELLOW_FILL
                                cell.font = YELLOW_FONT
                            else:
                                cell.fill = RED_FILL
                                cell.font = RED_FONT

                ws.row_dimensions[r_idx].height = 20

            # Peer Group Median Summary Row
            med_row_idx = len(group_df) + 2
            ws.cell(row=med_row_idx, column=1, value="—")
            ws.cell(row=med_row_idx, column=2, value="Group Median")
            ws.cell(row=med_row_idx, column=3, value="—")

            for c_idx, (raw_col, _, _) in enumerate(col_specs[3:], start=4):
                numeric_vals = pd.to_numeric(group_df[raw_col], errors="coerce").dropna()
                med_val = round(float(numeric_vals.median()), 2) if not numeric_vals.empty else "—"
                cell = ws.cell(row=med_row_idx, column=c_idx, value=med_val)
                cell.fill = MEDIAN_FILL
                cell.font = MEDIAN_FONT
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.border = THIN_BORDER

            for c_idx in (1, 2, 3):
                ws.cell(row=med_row_idx, column=c_idx).fill = MEDIAN_FILL
                ws.cell(row=med_row_idx, column=c_idx).font = MEDIAN_FONT
                ws.cell(row=med_row_idx, column=c_idx).border = THIN_BORDER

            ws.row_dimensions[med_row_idx].height = 22

            # Auto column widths
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 11)

            ws.freeze_panes = "A2"

        wb.save(output_path)
        logger.info("Saved peer comparison report to %s (%d sheets)", output_path, len(wb.sheetnames))
        return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    engine = PeerEngine()
    df_pp = engine.compute_peer_percentiles()
    print("Computed percentiles rows:", len(df_pp))
    excel_path = engine.export_peer_comparison_workbook()
    print("Peer comparison report generated at:", excel_path)
    radar_count = engine.generate_all_radar_charts()
    print("Radar charts generated:", radar_count)
