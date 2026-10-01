"""Sector & Peer Group PDF Report Generator (Epic 08, Day 35).

Generates comprehensive institutional PDF reports for all 11 peer group sectors.
Each report features:
- Executive summary with sector median benchmarks (P/E, P/B, ROE, D/E, OPM, 5Y Rev CAGR)
- Embedded comparative horizontal bar chart ranking constituents by Market Cap / ROE
- Detailed constituent metrics table with zebra striping and right-aligned financial figures
- Professional institutional styling and layout.
"""

from __future__ import annotations

import io
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(root_dir, "data", "nifty100.db")
if not os.path.exists(DEFAULT_DB_PATH) and os.path.exists(os.path.join(root_dir, "nifty100.db")):
    DEFAULT_DB_PATH = os.path.join(root_dir, "nifty100.db")

SECTOR_REPORTS_DIR = os.path.join(root_dir, "reports", "sector")


def sanitize_filename(name: str) -> str:
    """Sanitize sector name for filesystem path."""
    return re.sub(r"[^\w\-]", "_", name.strip())


class SectorReportGenerator:
    """Generates PDF benchmark reports for industry sectors and peer groups."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def _render_sector_chart(self, df_constituents: pd.DataFrame, metric_col: str, title: str) -> io.BytesIO:
        """Render a horizontal bar chart of constituents ranked by metric."""
        plot_df = df_constituents.sort_values(metric_col, ascending=True).copy()
        names = plot_df["company_id"].tolist()
        vals = plot_df[metric_col].fillna(0).tolist()

        fig, ax = plt.subplots(figsize=(6.8, max(2.2, len(names) * 0.35)), dpi=250)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f8fafc")

        y = range(len(names))
        bars = ax.barh(y, vals, height=0.55, color="#1e3a8a", alpha=0.9)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=7.5, fontweight="bold")
        ax.set_title(title, fontsize=8.5, fontweight="bold", pad=4, color="#0f172a")
        ax.tick_params(axis="both", labelsize=7)
        ax.grid(True, linestyle="--", alpha=0.4, axis="x")

        # Label values on bars
        max_val = max(vals) if vals and max(vals) > 0 else 1.0
        for bar in bars:
            w = bar.get_width()
            ax.text(
                w + (max_val * 0.01),
                bar.get_y() + bar.get_height() / 2,
                f"{w:,.1f}",
                va="center",
                fontsize=6.5,
                color="#334155",
            )

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=250)
        plt.close(fig)
        buf.seek(0)
        return buf

    def _render_roe_chart(self, df_constituents: pd.DataFrame, title: str) -> io.BytesIO:
        """Render horizontal bar chart of constituents ranked by Return on Equity."""
        plot_df = df_constituents.sort_values("return_on_equity_pct", ascending=True).copy()
        names = plot_df["company_id"].tolist()
        vals = plot_df["return_on_equity_pct"].fillna(0).tolist()

        fig, ax = plt.subplots(figsize=(6.8, max(2.2, len(names) * 0.35)), dpi=250)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f8fafc")

        y = range(len(names))
        bars = ax.barh(y, vals, height=0.55, color="#059669", alpha=0.9)
        ax.set_yticks(y)
        ax.set_yticklabels(names, fontsize=7.5, fontweight="bold")
        ax.set_title(title, fontsize=8.5, fontweight="bold", pad=4, color="#0f172a")
        ax.tick_params(axis="both", labelsize=7)
        ax.grid(True, linestyle="--", alpha=0.4, axis="x")

        max_val = max(vals) if vals and max(vals) > 0 else 1.0
        for bar in bars:
            w = bar.get_width()
            ax.text(
                w + (max_val * 0.01),
                bar.get_y() + bar.get_height() / 2,
                f"{w:,.1f}%",
                va="center",
                fontsize=6.5,
                color="#334155",
            )

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=250)
        plt.close(fig)
        buf.seek(0)
        return buf

    def generate_report(self, group_name: str, output_path: Optional[str] = None) -> str:
        """Generate PDF report for a given peer group or sector."""
        if output_path is None:
            os.makedirs(SECTOR_REPORTS_DIR, exist_ok=True)
            fname = f"{sanitize_filename(group_name)}_report.pdf"
            output_path = os.path.join(SECTOR_REPORTS_DIR, fname)

        conn = sqlite3.connect(self.db_path)
        try:
            # Query constituents in this peer group
            pg_df = pd.read_sql(
                f"SELECT company_id, is_benchmark FROM peer_groups WHERE peer_group_name = '{group_name}'",
                conn,
            )
            if pg_df.empty:
                # Fallback to broad_sector query if peer_group_name didn't match
                sec_df = pd.read_sql(
                    f"SELECT company_id FROM sectors WHERE broad_sector = '{group_name}'", conn
                )
                cids = sec_df["company_id"].tolist()
            else:
                cids = pg_df["company_id"].tolist()

            if not cids:
                raise ValueError(f"No companies found for sector/group '{group_name}'")

            cids_str = "', '".join(cids)
            comps_df = pd.read_sql(
                f"SELECT id, company_name FROM companies WHERE id IN ('{cids_str}')", conn
            )
            mc_df = pd.read_sql(
                f"SELECT company_id, market_cap_crore, pe_ratio, pb_ratio, dividend_yield_pct FROM market_cap WHERE company_id IN ('{cids_str}') AND year = '2024-03'",
                conn,
            )
            rf_df = pd.read_sql(
                f"SELECT company_id, year, return_on_equity_pct, roce_pct, debt_to_equity, operating_profit_margin_pct, revenue_cagr_5yr FROM financial_ratios WHERE company_id IN ('{cids_str}') AND year != 'TTM' ORDER BY company_id, year",
                conn,
            )
        finally:
            conn.close()

        # Isolate latest annual ratios per company
        latest_r_list = []
        for cid in cids:
            sub = rf_df[rf_df["company_id"] == cid]
            valid = sub[sub["operating_profit_margin_pct"].notna() | sub["return_on_equity_pct"].notna()]
            row = valid.iloc[-1].to_dict() if not valid.empty else (sub.iloc[-1].to_dict() if not sub.empty else {})
            row["company_id"] = cid
            latest_r_list.append(row)
        df_latest_r = pd.DataFrame(latest_r_list)

        # Merge constituent metrics
        merged = pd.merge(comps_df, mc_df, left_on="id", right_on="company_id", how="left")
        merged = pd.merge(merged, df_latest_r, left_on="id", right_on="company_id", how="left")
        merged["company_id"] = merged["id"]

        # Calculate Sector Medians
        med_pe = merged["pe_ratio"].dropna().median()
        med_pb = merged["pb_ratio"].dropna().median()
        med_roe = merged["return_on_equity_pct"].dropna().median()
        med_roce = merged["roce_pct"].dropna().median()
        med_de = merged["debt_to_equity"].dropna().median()
        med_opm = merged["operating_profit_margin_pct"].dropna().median()
        med_cagr = merged["revenue_cagr_5yr"].dropna().median()

        # Chart of Market Cap
        chart_buf = self._render_sector_chart(
            merged, "market_cap_crore", f"{group_name} Constituents by Market Cap (₹ Cr)"
        )

        # ReportLab Document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=24,
            rightMargin=24,
            topMargin=20,
            bottomMargin=20,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "SecTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            textColor=colors.HexColor("#ffffff"),
            leading=18,
        )
        subtitle_style = ParagraphStyle(
            "SecSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            textColor=colors.HexColor("#cbd5e1"),
            leading=11,
        )

        story: List[Any] = []

        # Header Banner
        left_h = [
            Paragraph(f"Sector Intelligence Report: {group_name}", title_style),
            Paragraph(f"Nifty 100 Index Coverage | Constituents: {len(merged)} Companies", subtitle_style),
        ]
        right_h = [
            Paragraph("<b>BENCHMARK REPORT</b>", ParagraphStyle("BR", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=colors.white, alignment=2)),
            Paragraph("Annual Audited Statements", ParagraphStyle("BRS", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#93c5fd"), alignment=2)),
        ]
        header_table = Table([[left_h, right_h]], colWidths=[370, 177])
        header_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(header_table)
        story.append(Spacer(1, 8))

        # Sector Median Benchmark Summary Cards (2 rows x 3 cols)
        def med_cell(lbl: str, val: str) -> List[Any]:
            return [
                Paragraph(f"<font size=6.5 color='#64748b'><b>{lbl}</b></font>", styles["Normal"]),
                Paragraph(f"<font size=10 color='#0f172a'><b>{val}</b></font>", styles["Normal"]),
            ]

        med_data = [
            [
                med_cell("MEDIAN P/E RATIO", f"{med_pe:.1f}x" if pd.notna(med_pe) else "N/A"),
                med_cell("MEDIAN P/B RATIO", f"{med_pb:.2f}x" if pd.notna(med_pb) else "N/A"),
                med_cell("MEDIAN RETURN ON EQUITY", f"{med_roe:.1f}%" if pd.notna(med_roe) else "N/A"),
            ],
            [
                med_cell("MEDIAN DEBT TO EQUITY", f"{med_de:.2f}x" if pd.notna(med_de) else "N/A"),
                med_cell("MEDIAN OPERATING MARGIN", f"{med_opm:.1f}%" if pd.notna(med_opm) else "N/A"),
                med_cell("MEDIAN 5-YR REVENUE CAGR", f"{med_cagr:.1f}%" if pd.notna(med_cagr) else "N/A"),
            ],
        ]
        med_table = Table(med_data, colWidths=[182, 182, 183])
        med_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(med_table)
        story.append(Spacer(1, 10))

        # Chart
        chart_img = Image(chart_buf, width=547, height=max(130, len(merged) * 22))
        story.append(chart_img)
        story.append(Spacer(1, 10))

        # Constituents Table
        story.append(
            Paragraph(
                f"<font size=9 color='#0f172a'><b>{group_name.upper()} CONSTITUENTS FINANCIAL METRICS</b></font>",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 4))

        th = ["Ticker", "Company", "Mkt Cap (Cr)", "P/E", "P/B", "ROE %", "ROCE %", "D/E", "OPM %", "5Y Rev CAGR"]
        t_rows = [th]
        for _, row in merged.sort_values("market_cap_crore", ascending=False).iterrows():
            cid = row["id"]
            cname = (row["company_name"] or "")[:18]
            mc = f"{row['market_cap_crore']:,.0f}" if pd.notna(row.get("market_cap_crore")) else "-"
            pe = f"{row['pe_ratio']:.1f}" if pd.notna(row.get("pe_ratio")) else "-"
            pb = f"{row['pb_ratio']:.2f}" if pd.notna(row.get("pb_ratio")) else "-"
            roe = f"{row['return_on_equity_pct']:.1f}" if pd.notna(row.get("return_on_equity_pct")) else "-"
            roce = f"{row['roce_pct']:.1f}" if pd.notna(row.get("roce_pct")) else "-"
            de = f"{row['debt_to_equity']:.2f}" if pd.notna(row.get("debt_to_equity")) else "-"
            opm = f"{row['operating_profit_margin_pct']:.1f}" if pd.notna(row.get("operating_profit_margin_pct")) else "-"
            rc = f"{row['revenue_cagr_5yr']:.1f}" if pd.notna(row.get("revenue_cagr_5yr")) else "-"
            t_rows.append([cid, cname, mc, pe, pb, roe, roce, de, opm, rc])

        t_const = Table(t_rows, colWidths=[55, 95, 68, 38, 38, 45, 45, 38, 45, 50])
        t_const.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.HexColor("#ffffff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ])
        )
        story.append(t_const)
        story.append(Spacer(1, 10))

        # Footer
        footer_p = Paragraph(
            "<font size=6.5 color='#64748b'><b>Source:</b> N100 Intelligence Platform. Data sourced from audited annual filings and normalized financial statements. Generated for institutional analysis.</font>",
            styles["Normal"],
        )
        story.append(footer_p)

        # Page 2: Profitability & Valuation Breakdown
        story.append(PageBreak())
        story.append(
            Paragraph(
                f"<font size=12 color='#1e3a8a'><b>{group_name.upper()} — PROFITABILITY & VALUATION BENCHMARK</b></font>",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 8))
        roe_buf = self._render_roe_chart(merged, f"{group_name} Constituents: Return on Equity (ROE %)")
        story.append(Image(roe_buf, width=547, height=max(130, len(merged) * 22)))
        story.append(Spacer(1, 10))

        # Secondary Valuation Table
        story.append(
            Paragraph(
                f"<font size=9 color='#0f172a'><b>VALUATION MULTIPLES & CAPITAL EFFICIENCY</b></font>",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 4))
        th2 = ["Ticker", "Company", "P/E", "P/B", "Div Yield %", "ROE %", "ROCE %", "OPM %"]
        t2_rows = [th2]
        for _, row in merged.sort_values("return_on_equity_pct", ascending=False).iterrows():
            cid = row["id"]
            cname = (row["company_name"] or "")[:20]
            pe = f"{row['pe_ratio']:.1f}" if pd.notna(row.get("pe_ratio")) else "-"
            pb = f"{row['pb_ratio']:.2f}" if pd.notna(row.get("pb_ratio")) else "-"
            dy = f"{row.get('dividend_yield_pct', 0.0):.2f}%" if pd.notna(row.get("dividend_yield_pct")) else "-"
            roe = f"{row['return_on_equity_pct']:.1f}%" if pd.notna(row.get("return_on_equity_pct")) else "-"
            roce = f"{row['roce_pct']:.1f}%" if pd.notna(row.get("roce_pct")) else "-"
            opm = f"{row['operating_profit_margin_pct']:.1f}%" if pd.notna(row.get("operating_profit_margin_pct")) else "-"
            t2_rows.append([cid, cname, pe, pb, dy, roe, roce, opm])
        t2 = Table(t2_rows, colWidths=[60, 130, 55, 55, 65, 55, 55, 55])
        t2.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "LEFT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.HexColor("#ffffff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ])
        )
        story.append(t2)
        story.append(Spacer(1, 10))
        story.append(footer_p)

        doc.build(story)
        sz = os.path.getsize(output_path)
        logger.info(f"Sector report for '{group_name}' generated: {sz} bytes ({sz/1024:.1f} KB)")
        return output_path

    def generate_all_sectors(self, output_dir: str = SECTOR_REPORTS_DIR) -> List[str]:
        """Generate all 11 peer group sector PDF reports."""
        os.makedirs(output_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            pg_names = pd.read_sql("SELECT DISTINCT peer_group_name FROM peer_groups ORDER BY peer_group_name", conn)[
                "peer_group_name"
            ].tolist()
        finally:
            conn.close()

        generated = []
        for name in pg_names:
            out_pdf = os.path.join(output_dir, f"{sanitize_filename(name)}_report.pdf")
            self.generate_report(name, out_pdf)
            generated.append(out_pdf)

        logger.info(f"Generated {len(generated)} sector reports in {output_dir}")
        return generated


def run_sector_reports() -> List[str]:
    """Convenience runner."""
    gen = SectorReportGenerator()
    return gen.generate_all_sectors()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_sector_reports()
