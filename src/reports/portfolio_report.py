"""Portfolio Summary Compendium PDF Report (Epic 08, Day 35).

Generates a master 92-company portfolio intelligence compendium PDF.
Features:
- Macro index overview (Total Market Cap, Median P/E, Median ROE, % Accelerating, % Deleveraging)
- Master institutional table across all 92 companies sorted alphabetically
- Directional momentum indicators for Revenue (3Y vs 5Y CAGR) and PAT (3Y vs 5Y CAGR)
- Deleveraging status badges
- Multi-page table with repeat headers and professional typography.
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
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(root_dir, "data", "nifty100.db")
if not os.path.exists(DEFAULT_DB_PATH) and os.path.exists(os.path.join(root_dir, "nifty100.db")):
    DEFAULT_DB_PATH = os.path.join(root_dir, "nifty100.db")

PORTFOLIO_DIR = os.path.join(root_dir, "reports", "portfolio")
INTEL_XLSX = os.path.join(root_dir, "output", "cashflow_intelligence.xlsx")


class NumberedCanvas(canvas.Canvas):
    """Canvas to add running page numbers and institutional footers."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Any] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor("#64748b"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(24, 25, 818, 25)

        # Footer texts
        self.drawString(
            24,
            15,
            "N100 Financial Intelligence Platform | Portfolio Compendium | Strictly for Institutional Research",
        )
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.drawRightString(818, 15, page_str)
        self.restoreState()


class PortfolioReportGenerator:
    """Master compendium PDF report generator for all 92 companies."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path

    def load_data(self) -> pd.DataFrame:
        """Load and merge core company, valuation, and ratio metrics."""
        conn = sqlite3.connect(self.db_path)
        try:
            df_comps = pd.read_sql("SELECT id, company_name FROM companies ORDER BY id", conn)
            df_sec = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
            df_mc = pd.read_sql(
                "SELECT company_id, market_cap_crore, pe_ratio, pb_ratio, dividend_yield_pct FROM market_cap WHERE year = '2024-03'",
                conn,
            )
            df_rf = pd.read_sql(
                "SELECT company_id, year, return_on_equity_pct, debt_to_equity, revenue_cagr_3yr, revenue_cagr_5yr, pat_cagr_3yr, pat_cagr_5yr FROM financial_ratios WHERE year != 'TTM' ORDER BY company_id, year",
                conn,
            )
            df_sp = pd.read_sql(
                "SELECT company_id, close_price, date FROM stock_prices ORDER BY date", conn
            )
        finally:
            conn.close()

        # Load cash flow intelligence for deleveraging flags
        df_intel = pd.read_excel(INTEL_XLSX) if os.path.exists(INTEL_XLSX) else pd.DataFrame()
        delev_map = (
            dict(zip(df_intel["company_id"], df_intel["deleveraging_flag"]))
            if not df_intel.empty
            else {}
        )

        # Latest ratios
        latest_r_list = []
        for cid in df_comps["id"]:
            sub = df_rf[df_rf["company_id"] == cid]
            valid = sub[sub["return_on_equity_pct"].notna() | sub["debt_to_equity"].notna()]
            row = valid.iloc[-1].to_dict() if not valid.empty else (sub.iloc[-1].to_dict() if not sub.empty else {})
            row["company_id"] = cid
            latest_r_list.append(row)
        df_latest_r = pd.DataFrame(latest_r_list)

        # Latest stock prices
        latest_sp = df_sp.groupby("company_id").last().reset_index()

        # Clean merges by standardizing on 'id'
        m = df_comps.copy()
        sec_clean = df_sec.drop_duplicates("company_id").rename(columns={"company_id": "id"})
        mc_clean = df_mc.drop_duplicates("company_id").rename(columns={"company_id": "id"})
        r_clean = df_latest_r.drop_duplicates("company_id").rename(columns={"company_id": "id"})
        sp_clean = latest_sp.drop_duplicates("company_id")[["company_id", "close_price"]].rename(columns={"company_id": "id"})

        m = pd.merge(m, sec_clean, on="id", how="left")
        m = pd.merge(m, mc_clean, on="id", how="left")
        m = pd.merge(m, r_clean, on="id", how="left")
        m = pd.merge(m, sp_clean, on="id", how="left")
        m["deleveraging_flag"] = m["id"].map(delev_map).fillna(False)

        return m

    def generate(self, output_path: Optional[str] = None) -> str:
        """Build and render landscape master portfolio compendium."""
        if output_path is None:
            os.makedirs(PORTFOLIO_DIR, exist_ok=True)
            output_path = os.path.join(PORTFOLIO_DIR, "portfolio_summary.pdf")

        df = self.load_data()

        # Calculate macro metrics
        tot_mkt_cap = df["market_cap_crore"].dropna().sum()
        med_pe = df["pe_ratio"].dropna().median()
        med_roe = df["return_on_equity_pct"].dropna().median()

        # Revenue momentum: 3yr vs 5yr
        rev_accel_count = sum(
            (df["revenue_cagr_3yr"] > df["revenue_cagr_5yr"] + 0.5)
            & df["revenue_cagr_3yr"].notna()
            & df["revenue_cagr_5yr"].notna()
        )
        rev_accel_pct = (rev_accel_count / len(df)) * 100

        delev_count = sum(df["deleveraging_flag"] == True)
        delev_pct = (delev_count / len(df)) * 100

        # Document setup (Landscape A4: 842 x 595 pt)
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(A4),
            leftMargin=24,
            rightMargin=24,
            topMargin=22,
            bottomMargin=35,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "PortTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=colors.HexColor("#ffffff"),
            leading=19,
        )
        subtitle_style = ParagraphStyle(
            "PortSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            textColor=colors.HexColor("#cbd5e1"),
            leading=11,
        )

        story: List[Any] = []

        # Header Banner
        left_h = [
            Paragraph("Nifty 100 Complete Financial Intelligence Compendium", title_style),
            Paragraph(f"Cross-Sectional Valuation, Profitability & Growth Momentum Matrix | {len(df)} Tracked Companies", subtitle_style),
        ]
        right_h = [
            Paragraph("<b>INSTITUTIONAL PORTFOLIO REPORT</b>", ParagraphStyle("IPR", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.5, textColor=colors.white, alignment=2)),
            Paragraph("Full Audited Coverage (FY11 - FY24)", ParagraphStyle("IPRS", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#93c5fd"), alignment=2)),
        ]
        header_table = Table([[left_h, right_h]], colWidths=[530, 264])
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

        # KPI Metrics Cards (1 row x 5 cols)
        def kpi_card(lbl: str, val: str) -> List[Any]:
            return [
                Paragraph(f"<font size=6.5 color='#64748b'><b>{lbl}</b></font>", styles["Normal"]),
                Paragraph(f"<font size=10.5 color='#0f172a'><b>{val}</b></font>", styles["Normal"]),
            ]

        summary_cards = [[
            kpi_card("TOTAL MARKET CAP", f"₹{tot_mkt_cap/1e5:,.1f} Lakh Cr"),
            kpi_card("MEDIAN P/E RATIO", f"{med_pe:.1f}x"),
            kpi_card("MEDIAN ROE", f"{med_roe:.1f}%"),
            kpi_card("REV ACCELERATION", f"{rev_accel_pct:.1f}% ({rev_accel_count}/{len(df)})"),
            kpi_card("DELEVERAGING SHARE", f"{delev_pct:.1f}% ({delev_count}/{len(df)})"),
        ]]
        t_summary = Table(summary_cards, colWidths=[158, 158, 158, 160, 160])
        t_summary.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(t_summary)
        story.append(Spacer(1, 9))

        # Master Table Headers
        headers = [
            "Ticker",
            "Company Name",
            "Sector",
            "CMP (₹)",
            "Mkt Cap (Cr)",
            "P/E",
            "P/B",
            "ROE %",
            "D/E",
            "Rev Momentum",
            "PAT Momentum",
            "Deleveraging",
        ]
        table_rows = [headers]

        for _, row in df.sort_values("id").iterrows():
            cid = row["id"]
            cname = (row["company_name"] or "")[:20]
            sec = (row["broad_sector"] or "")[:15]
            cmp = f"{row['close_price']:,.1f}" if pd.notna(row.get("close_price")) else "-"
            mc = f"{row['market_cap_crore']:,.0f}" if pd.notna(row.get("market_cap_crore")) else "-"
            pe = f"{row['pe_ratio']:.1f}" if pd.notna(row.get("pe_ratio")) else "-"
            pb = f"{row['pb_ratio']:.2f}" if pd.notna(row.get("pb_ratio")) else "-"
            roe = f"{row['return_on_equity_pct']:.1f}" if pd.notna(row.get("return_on_equity_pct")) else "-"
            de = f"{row['debt_to_equity']:.2f}" if pd.notna(row.get("debt_to_equity")) else "-"

            # Directional Momentum - Revenue
            r3, r5 = row.get("revenue_cagr_3yr"), row.get("revenue_cagr_5yr")
            if pd.notna(r3) and pd.notna(r5):
                if r3 > r5 + 0.5:
                    rev_mom = "<font color='#16a34a'><b>[&#8593; Accel]</b></font>"
                elif r3 < r5 - 0.5:
                    rev_mom = "<font color='#dc2626'><b>[&#8595; Decel]</b></font>"
                else:
                    rev_mom = "<font color='#64748b'>[&#8594; Flat]</font>"
            else:
                rev_mom = "-"

            # Directional Momentum - PAT
            p3, p5 = row.get("pat_cagr_3yr"), row.get("pat_cagr_5yr")
            if pd.notna(p3) and pd.notna(p5):
                if p3 > p5 + 0.5:
                    pat_mom = "<font color='#16a34a'><b>[&#8593; Accel]</b></font>"
                elif p3 < p5 - 0.5:
                    pat_mom = "<font color='#dc2626'><b>[&#8595; Decel]</b></font>"
                else:
                    pat_mom = "<font color='#64748b'>[&#8594; Flat]</font>"
            else:
                pat_mom = "-"

            # Deleveraging status
            is_delev = row.get("deleveraging_flag")
            if is_delev:
                delev_str = "<font color='#15803d'><b>YES</b></font>"
            elif pd.notna(row.get("debt_to_equity")) and row.get("debt_to_equity") == 0:
                delev_str = "<font color='#2563eb'>DEBT FREE</font>"
            else:
                delev_str = "<font color='#94a3b8'>NO</font>"

            table_rows.append([
                cid,
                cname,
                sec,
                cmp,
                mc,
                pe,
                pb,
                roe,
                de,
                Paragraph(rev_mom, styles["Normal"]),
                Paragraph(pat_mom, styles["Normal"]),
                Paragraph(delev_str, styles["Normal"]),
            ])

        # Master Table Layout
        col_widths = [56, 120, 95, 52, 65, 38, 38, 42, 38, 85, 85, 80]
        master_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
        master_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ALIGN", (1, 1), (2, -1), "LEFT"),
                ("ALIGN", (3, 1), (8, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.HexColor("#ffffff")]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(master_table)

        doc.build(story, canvasmaker=NumberedCanvas)
        sz = os.path.getsize(output_path)
        reader = PdfReader(output_path)
        logger.info(f"Portfolio Summary generated: {sz} bytes ({sz/1024:.1f} KB), {len(reader.pages)} pages")
        return output_path


def run_portfolio_report() -> str:
    """Convenience runner."""
    gen = PortfolioReportGenerator()
    return gen.generate()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_portfolio_report()
