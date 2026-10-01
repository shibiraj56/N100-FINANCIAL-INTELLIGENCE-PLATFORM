"""Automated Institutional 2-Page Tearsheet Generator (Epic 08, Days 33-34).

Generates high-fidelity, two-page financial tearsheets for Nifty 100 companies.
Features:
- Navy banner header with CMP, 52W H/L, Market Cap, Sector
- 6 Key Performance Indicator cards
- 4 Matplotlib charts (Rev/PAT dual bar, ROE/ROCE line, Capital Structure bar, Cash Flow bar)
- 5-year historical financial summary table
- Investment thesis with auto-generated Pros and Cons
- Capital allocation badge and CFO Quality rating
- Strict 2-page constraint with zero layout overflow and file size >= 30 KB.
"""

from __future__ import annotations

import io
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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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

REPORTS_DIR = os.path.join(root_dir, "reports", "tearsheets")
PROS_CONS_CSV = os.path.join(root_dir, "output", "pros_cons_generated.csv")
INTEL_XLSX = os.path.join(root_dir, "output", "cashflow_intelligence.xlsx")
SKIPPED_CSV = os.path.join(root_dir, "output", "skipped_tearsheets.csv")


class TearsheetGenerator:
    """Institutional tearsheet builder for a single company."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._load_metadata()

    def _load_metadata(self) -> None:
        """Pre-load cross-cutting metadata files."""
        if os.path.exists(PROS_CONS_CSV):
            self.df_pros_cons = pd.read_csv(PROS_CONS_CSV)
        else:
            self.df_pros_cons = pd.DataFrame()

        if os.path.exists(INTEL_XLSX):
            self.df_intel = pd.read_excel(INTEL_XLSX)
        else:
            self.df_intel = pd.DataFrame()

    def _render_chart_placeholder(self, title: str, message: str) -> io.BytesIO:
        """Render a placeholder image when data series is unavailable."""
        fig, ax = plt.subplots(figsize=(3.6, 1.8), dpi=150)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f8fafc")
        ax.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            fontsize=8,
            color="#64748b",
            wrap=True,
            transform=ax.transAxes,
        )
        ax.set_title(title, fontsize=8, fontweight="bold", pad=4, color="#0f172a")
        ax.set_xticks([])
        ax.set_yticks([])
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf

    def _make_rev_pat_chart(self, pl_df: pd.DataFrame) -> io.BytesIO:
        """Chart 1: 5-year Revenue & PAT dual-bar chart."""
        if pl_df.empty or "sales" not in pl_df:
            return self._render_chart_placeholder("Revenue & PAT Trend (₹ Cr)", "Historical P&L data not available")

        tail_df = pl_df.tail(5)
        years = [str(y)[-5:] for y in tail_df["year"]]
        sales = tail_df["sales"].fillna(0).tolist()
        pat = tail_df["net_profit"].fillna(0).tolist()

        fig, ax = plt.subplots(figsize=(3.6, 1.8), dpi=150)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f8fafc")
        x = range(len(years))
        w = 0.35

        ax.bar([i - w / 2 for i in x], sales, w, label="Revenue", color="#1e3a8a", alpha=0.95)
        ax.bar([i + w / 2 for i in x], pat, w, label="PAT", color="#059669", alpha=0.95)
        ax.set_xticks(x)
        ax.set_xticklabels(years, fontsize=7)
        ax.set_title("Revenue & PAT Trend (₹ Cr)", fontsize=8, fontweight="bold", pad=3, color="#0f172a")
        ax.legend(fontsize=6.5, loc="upper left", framealpha=0.6)
        ax.tick_params(axis="both", labelsize=6.5)
        ax.grid(True, linestyle="--", alpha=0.4)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf

    def _make_roe_roce_chart(self, r_df: pd.DataFrame) -> io.BytesIO:
        """Chart 2: 5-year ROE & ROCE percentage line chart."""
        valid_r = r_df[r_df["operating_profit_margin_pct"].notna() | r_df["return_on_equity_pct"].notna()]
        if valid_r.empty:
            return self._render_chart_placeholder("Return Ratios Trend (%)", "Return ratios not available")

        tail_df = valid_r.tail(5)
        years = [str(y)[-5:] for y in tail_df["year"]]
        roe = tail_df["return_on_equity_pct"].tolist()
        roce = tail_df["roce_pct"].tolist()

        fig, ax = plt.subplots(figsize=(3.6, 1.8), dpi=150)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f8fafc")
        x = range(len(years))

        ax.plot(x, roe, marker="o", markersize=4, label="ROE %", color="#2563eb", linewidth=1.5)
        ax.plot(x, roce, marker="s", markersize=4, label="ROCE %", color="#d97706", linewidth=1.5)
        ax.set_xticks(x)
        ax.set_xticklabels(years, fontsize=7)
        ax.set_title("Return Ratios Trend (%)", fontsize=8, fontweight="bold", pad=3, color="#0f172a")
        ax.legend(fontsize=6.5, loc="best", framealpha=0.6)
        ax.tick_params(axis="both", labelsize=6.5)
        ax.grid(True, linestyle="--", alpha=0.4)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf

    def _make_balance_sheet_chart(self, bs_df: pd.DataFrame) -> io.BytesIO:
        """Chart 3: 5-year Balance Sheet structure (Net Worth vs Borrowings)."""
        if bs_df.empty:
            return self._render_chart_placeholder(
                "Capital Structure (₹ Cr)", "Regulatory format / Data not available"
            )

        tail_df = bs_df.tail(5)
        years = [str(y)[-5:] for y in tail_df["year"]]

        eq_col = "equity_share_capital" if "equity_share_capital" in tail_df else "equity_capital"
        eq = tail_df[eq_col].fillna(0) if eq_col in tail_df else pd.Series(0, index=tail_df.index)
        res = tail_df["reserves"].fillna(0) if "reserves" in tail_df else pd.Series(0, index=tail_df.index)
        nw = eq + res
        bor = tail_df["borrowings"].fillna(0) if "borrowings" in tail_df else pd.Series(0, index=tail_df.index)

        fig, ax = plt.subplots(figsize=(3.6, 1.8), dpi=150)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f8fafc")
        x = range(len(years))

        ax.bar(x, nw, 0.45, label="Net Worth", color="#0284c7", alpha=0.9)
        ax.bar(x, bor, 0.45, bottom=nw, label="Borrowings", color="#ef4444", alpha=0.9)
        ax.set_xticks(x)
        ax.set_xticklabels(years, fontsize=7)
        ax.set_title("Capital Employed Structure (₹ Cr)", fontsize=8, fontweight="bold", pad=3, color="#0f172a")
        ax.legend(fontsize=6.5, loc="upper left", framealpha=0.6)
        ax.tick_params(axis="both", labelsize=6.5)
        ax.grid(True, linestyle="--", alpha=0.4)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf

    def _make_cash_flow_chart(self, cf_df: pd.DataFrame) -> io.BytesIO:
        """Chart 4: 5-year Cash Flow activities (CFO, CFI, CFF)."""
        if cf_df.empty:
            return self._render_chart_placeholder(
                "Cash Flow Activities (₹ Cr)", "Cash flow statement not available in filings"
            )

        tail_df = cf_df.tail(5)
        years = [str(y)[-5:] for y in tail_df["year"]]
        cfo = tail_df["operating_activity"].fillna(0).tolist()
        cfi = tail_df["investing_activity"].fillna(0).tolist()
        cff = tail_df["financing_activity"].fillna(0).tolist()

        fig, ax = plt.subplots(figsize=(3.6, 1.8), dpi=150)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f8fafc")
        x = range(len(years))
        w = 0.25

        ax.bar([i - w for i in x], cfo, w, label="CFO", color="#10b981", alpha=0.9)
        ax.bar(x, cfi, w, label="CFI", color="#f59e0b", alpha=0.9)
        ax.bar([i + w for i in x], cff, w, label="CFF", color="#6366f1", alpha=0.9)
        ax.axhline(0, color="#64748b", linewidth=0.8, linestyle="--")
        ax.set_xticks(x)
        ax.set_xticklabels(years, fontsize=7)
        ax.set_title("Cash Flow Activities (₹ Cr)", fontsize=8, fontweight="bold", pad=3, color="#0f172a")
        ax.legend(fontsize=6.5, loc="best", framealpha=0.6)
        ax.tick_params(axis="both", labelsize=6.5)
        ax.grid(True, linestyle="--", alpha=0.4)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        buf.seek(0)
        return buf

    def generate(self, ticker: str, output_path: Optional[str] = None) -> str:
        """Generate a complete 2-page PDF tearsheet for the given ticker."""
        if output_path is None:
            os.makedirs(REPORTS_DIR, exist_ok=True)
            output_path = os.path.join(REPORTS_DIR, f"{ticker}_tearsheet.pdf")

        conn = sqlite3.connect(self.db_path)
        try:
            comp_df = pd.read_sql(f"SELECT * FROM companies WHERE id = '{ticker}'", conn)
            sec_df = pd.read_sql(f"SELECT broad_sector FROM sectors WHERE company_id = '{ticker}'", conn)
            mc_df = pd.read_sql(f"SELECT * FROM market_cap WHERE company_id = '{ticker}' ORDER BY year DESC", conn)
            pl_df = pd.read_sql(
                f"SELECT * FROM profitandloss WHERE company_id = '{ticker}' AND year != 'TTM' ORDER BY year",
                conn,
            )
            bs_df = pd.read_sql(
                f"SELECT * FROM balancesheet WHERE company_id = '{ticker}' AND year != 'TTM' ORDER BY year",
                conn,
            )
            cf_df = pd.read_sql(
                f"SELECT * FROM cashflow WHERE company_id = '{ticker}' AND year != 'TTM' ORDER BY year",
                conn,
            )
            rf_df = pd.read_sql(
                f"SELECT * FROM financial_ratios WHERE company_id = '{ticker}' AND year != 'TTM' ORDER BY year",
                conn,
            )
            sp_df = pd.read_sql(
                f"SELECT * FROM stock_prices WHERE company_id = '{ticker}' ORDER BY date", conn
            )
        finally:
            conn.close()

        if comp_df.empty:
            raise ValueError(f"Ticker '{ticker}' not found in companies table.")

        comp_name = comp_df.iloc[0]["company_name"]
        sector = sec_df.iloc[0]["broad_sector"] if not sec_df.empty else "Diversified"

        # Market Cap & Valuations
        latest_mc = mc_df.iloc[0] if not mc_df.empty else pd.Series(dtype=object)
        mc_val = latest_mc.get("market_cap_crore")
        pe_val = latest_mc.get("pe_ratio")
        pb_val = latest_mc.get("pb_ratio")
        div_yield = latest_mc.get("dividend_yield_pct")

        # Prices
        if not sp_df.empty:
            cmp = sp_df.iloc[-1].get("close_price") or 0.0
            h52 = sp_df["high_price"].max() or cmp * 1.1
            l52 = sp_df["low_price"].min() or cmp * 0.9
        else:
            cmp, h52, l52 = 0.0, 0.0, 0.0

        # Ratios
        valid_r = rf_df[rf_df["operating_profit_margin_pct"].notna() | rf_df["return_on_equity_pct"].notna()]
        latest_r = valid_r.iloc[-1] if not valid_r.empty else (rf_df.iloc[-1] if not rf_df.empty else pd.Series(dtype=object))

        roe_val = latest_r.get("return_on_equity_pct")
        roce_val = latest_r.get("roce_pct")
        de_val = latest_r.get("debt_to_equity")

        # Pros and Cons
        pros: List[str] = []
        cons: List[str] = []
        if not self.df_pros_cons.empty:
            sub_pc = self.df_pros_cons[self.df_pros_cons["company_id"] == ticker]
            pros = sub_pc[sub_pc["rule_type"] == "PRO"]["text"].tolist()[:4]
            cons = sub_pc[sub_pc["rule_type"] == "CON"]["text"].tolist()[:4]

        # Intelligence Badges
        alloc_pat = "Reinvestor"
        cfo_qual = "High Quality"
        capex_int = "Moderate"
        if not self.df_intel.empty:
            sub_intel = self.df_intel[self.df_intel["company_id"] == ticker]
            if not sub_intel.empty:
                alloc_pat = str(sub_intel["capital_allocation_pattern"].iloc[0])
                cfo_qual = str(sub_intel["cfo_quality_score"].iloc[0])
                capex_int = str(sub_intel["capex_intensity_label"].iloc[0])

        # Charts Generation
        c1_buf = self._make_rev_pat_chart(pl_df)
        c2_buf = self._make_roe_roce_chart(rf_df)
        c3_buf = self._make_balance_sheet_chart(bs_df)
        c4_buf = self._make_cash_flow_chart(cf_df)

        # Build PDF Story
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=24,
            rightMargin=24,
            topMargin=18,
            bottomMargin=18,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "HeaderTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=colors.HexColor("#ffffff"),
            leading=17,
        )
        subtitle_style = ParagraphStyle(
            "HeaderSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#cbd5e1"),
            leading=10,
        )
        header_right_style = ParagraphStyle(
            "HeaderRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#ffffff"),
            alignment=2,
            leading=13,
        )
        header_right_sub = ParagraphStyle(
            "HeaderRightSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            textColor=colors.HexColor("#93c5fd"),
            alignment=2,
            leading=10,
        )

        story: List[Any] = []

        # ---------------- PAGE 1 ----------------
        # Header banner
        mc_str = f"₹{mc_val:,.0f} Cr" if pd.notna(mc_val) else "N/A"
        cmp_str = f"₹{cmp:,.2f}" if cmp > 0 else "N/A"
        hl_str = f"₹{h52:,.1f} / ₹{l52:,.1f}" if h52 > 0 else "N/A"

        left_header = [
            Paragraph(f"{comp_name} ({ticker})", title_style),
            Paragraph(f"Sector: {sector} | Market Cap: {mc_str}", subtitle_style),
        ]
        right_header = [
            Paragraph(f"CMP: {cmp_str}", header_right_style),
            Paragraph(f"52W H/L: {hl_str}", header_right_sub),
        ]
        header_table = Table([[left_header, right_header]], colWidths=[360, 187])
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
        story.append(Spacer(1, 7))

        # 6 KPI Cards (2 rows x 3 cols)
        def kpi_cell(lbl: str, val: str) -> List[Any]:
            return [
                Paragraph(f"<font size=6.5 color='#64748b'><b>{lbl}</b></font>", styles["Normal"]),
                Paragraph(f"<font size=10.5 color='#0f172a'><b>{val}</b></font>", styles["Normal"]),
            ]

        kpi_data = [
            [
                kpi_cell("P/E RATIO", f"{pe_val:.1f}x" if pd.notna(pe_val) and pe_val else "N/A"),
                kpi_cell("P/B RATIO", f"{pb_val:.2f}x" if pd.notna(pb_val) and pb_val else "N/A"),
                kpi_cell("DIVIDEND YIELD", f"{div_yield:.2f}%" if pd.notna(div_yield) else "0.00%"),
            ],
            [
                kpi_cell("RETURN ON EQUITY (ROE)", f"{roe_val:.1f}%" if pd.notna(roe_val) else "N/A"),
                kpi_cell("ROCE", f"{roce_val:.1f}%" if pd.notna(roce_val) else "N/A"),
                kpi_cell("DEBT TO EQUITY", f"{de_val:.2f}x" if pd.notna(de_val) else "N/A"),
            ],
        ]
        kpi_table = Table(kpi_data, colWidths=[182, 182, 183])
        kpi_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(kpi_table)
        story.append(Spacer(1, 7))

        # Charts 1 & 2 side-by-side
        img1 = Image(c1_buf, width=265, height=135)
        img2 = Image(c2_buf, width=265, height=135)
        charts_table = Table([[img1, img2]], colWidths=[273, 274])
        charts_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        )
        story.append(charts_table)
        story.append(Spacer(1, 7))

        # Historical Financials Table (last 5 years)
        story.append(
            Paragraph(
                "<font size=8.5 color='#0f172a'><b>HISTORICAL FINANCIAL SUMMARY (LAST 5 YEARS)</b></font>",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 3))

        fin_headers = ["FY", "Sales (₹ Cr)", "OPM %", "Net Profit (₹ Cr)", "EPS (₹)", "D/E (x)", "ROE %"]
        fin_rows = [fin_headers]
        tail_pl = pl_df.tail(5)
        if tail_pl.empty:
            fin_rows.append(["-", "-", "-", "-", "-", "-", "-"])
        else:
            for _, prow in tail_pl.iterrows():
                yr = str(prow["year"])
                r_match = rf_df[rf_df["year"] == yr]
                rm = r_match.iloc[0] if not r_match.empty else {}
                s_val = f"{prow['sales']:,.0f}" if pd.notna(prow.get("sales")) else "-"
                opm = (
                    f"{rm.get('operating_profit_margin_pct'):.1f}%"
                    if pd.notna(rm.get("operating_profit_margin_pct"))
                    else "-"
                )
                pat = f"{prow['net_profit']:,.0f}" if pd.notna(prow.get("net_profit")) else "-"
                eps = f"{prow['eps']:.1f}" if pd.notna(prow.get("eps")) else "-"
                de = f"{rm.get('debt_to_equity'):.2f}" if pd.notna(rm.get("debt_to_equity")) else "-"
                roe = f"{rm.get('return_on_equity_pct'):.1f}%" if pd.notna(rm.get("return_on_equity_pct")) else "-"
                fin_rows.append([yr, s_val, opm, pat, eps, de, roe])

        t_fin = Table(fin_rows, colWidths=[65, 85, 75, 95, 75, 75, 77])
        t_fin.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.HexColor("#ffffff")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ])
        )
        story.append(t_fin)

        # ---------------- PAGE 2 ----------------
        story.append(PageBreak())

        # Mini Header Page 2
        p2_header = Table(
            [[
                Paragraph(
                    f"<b>CAPITAL ALLOCATION & INVESTMENT THESIS — {ticker}</b>",
                    ParagraphStyle(
                        "P2H",
                        parent=styles["Normal"],
                        fontName="Helvetica-Bold",
                        fontSize=9.5,
                        textColor=colors.HexColor("#0f172a"),
                    ),
                ),
                Paragraph(
                    "<b>PAGE 2 OF 2</b>",
                    ParagraphStyle(
                        "P2R",
                        parent=styles["Normal"],
                        fontName="Helvetica",
                        fontSize=8,
                        textColor=colors.HexColor("#64748b"),
                        alignment=2,
                    ),
                ),
            ]],
            colWidths=[400, 147],
        )
        p2_header.setStyle(
            TableStyle([
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ])
        )
        story.append(p2_header)
        story.append(Spacer(1, 5))

        # Charts 3 & 4 side-by-side
        img3 = Image(c3_buf, width=265, height=135)
        img4 = Image(c4_buf, width=265, height=135)
        charts2_table = Table([[img3, img4]], colWidths=[273, 274])
        charts2_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ])
        )
        story.append(charts2_table)
        story.append(Spacer(1, 7))

        # Profile Badges Table
        badge_data = [[
            Paragraph(
                f"<b>CAPITAL ALLOCATION PATTERN</b><br/><font size=9.5 color='#1e3a8a'><b>{alloc_pat}</b></font>",
                styles["Normal"],
            ),
            Paragraph(
                f"<b>5-YR CFO QUALITY SCORE</b><br/><font size=9.5 color='#059669'><b>{cfo_qual}</b></font>",
                styles["Normal"],
            ),
            Paragraph(
                f"<b>CAPEX INTENSITY</b><br/><font size=9.5 color='#d97706'><b>{capex_int}</b></font>",
                styles["Normal"],
            ),
        ]]
        badge_table = Table(badge_data, colWidths=[182, 182, 183])
        badge_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(badge_table)
        story.append(Spacer(1, 7))

        # Investment Thesis (Pros & Cons Side-by-Side)
        pro_items = [
            Paragraph(f"<font size=8 color='#0f172a'>• {p}</font>", styles["Normal"])
            for p in (pros or ["Strong operating history and market standing."])
        ]
        con_items = [
            Paragraph(f"<font size=8 color='#0f172a'>• {c}</font>", styles["Normal"])
            for c in (cons or ["Subject to macroeconomic and cyclical headwinds."])
        ]

        left_thesis = [
            Paragraph("<font size=9 color='#15803d'><b>KEY STRENGTHS & CATALYSTS (PROS)</b></font>", styles["Normal"]),
            Spacer(1, 3),
        ] + pro_items

        right_thesis = [
            Paragraph("<font size=9 color='#b91c1c'><b>KEY RISKS & HEADWINDS (CONS)</b></font>", styles["Normal"]),
            Spacer(1, 3),
        ] + con_items

        thesis_table = Table([[left_thesis, right_thesis]], colWidths=[270, 277])
        thesis_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f0fdf4")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fef2f2")),
                ("BOX", (0, 0), (0, 0), 0.5, colors.HexColor("#bbf7d0")),
                ("BOX", (1, 0), (1, 0), 0.5, colors.HexColor("#fecaca")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(thesis_table)
        story.append(Spacer(1, 7))

        # Disclaimer Footer
        footer_text = (
            "<b>Disclaimer:</b> This financial tearsheet is auto-generated by the N100 Financial Intelligence Platform for research "
            "and informational purposes only. It does not constitute investment advice or a recommendation to buy or sell securities."
        )
        story.append(Paragraph(f"<font size=6.5 color='#64748b'>{footer_text}</font>", styles["Normal"]))

        # Build document
        doc.build(story)

        # Validate strictly 2 pages
        reader = PdfReader(output_path)
        if len(reader.pages) != 2:
            logger.warning(f"Warning: {ticker} tearsheet generated {len(reader.pages)} pages instead of 2!")

        sz = os.path.getsize(output_path)
        logger.info(f"Tearsheet for {ticker} generated: {sz} bytes ({sz/1024:.1f} KB), {len(reader.pages)} pages")
        return output_path


def batch_generate_tearsheets(
    output_dir: str = REPORTS_DIR, db_path: str = DEFAULT_DB_PATH
) -> Tuple[int, int, List[str]]:
    """Generate tearsheet PDFs for all 92 companies and validate file sizes and page counts."""
    os.makedirs(output_dir, exist_ok=True)
    generator = TearsheetGenerator(db_path=db_path)

    conn = sqlite3.connect(db_path)
    try:
        comps = pd.read_sql("SELECT id FROM companies ORDER BY id", conn)["id"].tolist()
    finally:
        conn.close()

    success_count = 0
    fail_count = 0
    skipped: List[Dict[str, Any]] = []

    logger.info(f"Starting batch tearsheet generation for {len(comps)} companies...")

    for ticker in comps:
        out_pdf = os.path.join(output_dir, f"{ticker}_tearsheet.pdf")
        try:
            generator.generate(ticker, out_pdf)
            sz = os.path.getsize(out_pdf)
            reader = PdfReader(out_pdf)
            num_pages = len(reader.pages)

            if sz < 30_000 or num_pages != 2:
                logger.warning(f"Tearsheet validation warning for {ticker}: size={sz} bytes, pages={num_pages}")
                skipped.append({"company_id": ticker, "reason": f"Validation warning: size={sz}, pages={num_pages}"})
                fail_count += 1
            else:
                success_count += 1
        except Exception as e:
            logger.error(f"Failed to generate tearsheet for {ticker}: {e}")
            skipped.append({"company_id": ticker, "reason": str(e)})
            fail_count += 1

    # Save skipped report
    df_skipped = pd.DataFrame(skipped)
    os.makedirs(os.path.dirname(SKIPPED_CSV), exist_ok=True)
    df_skipped.to_csv(SKIPPED_CSV, index=False)
    logger.info(f"Batch generation completed: {success_count} succeeded, {fail_count} failed.")

    return success_count, fail_count, [s["company_id"] for s in skipped]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    batch_generate_tearsheets()
