"""Sector Analysis Screen — Landscape Bubble Chart & Medians (Day 25)."""

from __future__ import annotations

import sys
from pathlib import Path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_companies, get_sectors
from src.screener.engine import ScreenerEngine

st.title("🏭 Sector Landscape & Structural Valuation")
st.markdown("Analyze industry clustering, sub-sector dispersion, and median operational benchmarks across Nifty 100 sectors.")

@st.cache_data(ttl=600)
def load_universe():
    engine = ScreenerEngine()
    return engine.get_universe_data(year="2024-03")

df_universe = load_universe()

# Sector Dropdown Filter
sector_options = ["All Sectors"] + sorted(df_universe["broad_sector"].dropna().unique().tolist())
selected_sector = st.selectbox("Select Sector:", sector_options, index=0)

if selected_sector != "All Sectors":
    df_filtered = df_universe[df_universe["broad_sector"] == selected_sector].copy()
else:
    df_filtered = df_universe.copy()

# 1. Bubble Chart: X=Revenue, Y=ROE, Size=Market Cap, Color=Sub-sector
st.subheader(f"🌐 Sector Bubble Map ({selected_sector})")
st.caption("X-axis: Revenue (₹ Cr) | Y-axis: ROE (%) | Bubble Size: Market Cap (₹ Cr) | Color: Sub-Sector")

# Clean numerical data for plotting
plot_df = df_filtered.dropna(subset=["sales", "return_on_equity_pct", "market_cap_crore"]).copy()
plot_df["market_cap_bubble"] = plot_df["market_cap_crore"].clip(lower=1000)

fig_bubble = px.scatter(
    plot_df,
    x="sales",
    y="return_on_equity_pct",
    size="market_cap_bubble",
    color="sub_sector",
    hover_name="company_id",
    hover_data={
        "company_name": True,
        "sales": ":,.0f",
        "return_on_equity_pct": ":.2f",
        "market_cap_crore": ":,.0f",
        "pe_ratio": ":.1f",
        "market_cap_bubble": False,
    },
    labels={
        "sales": "Revenue / Sales (₹ Cr)",
        "return_on_equity_pct": "Return on Equity (ROE %)",
        "sub_sector": "Sub-Sector",
    },
    color_discrete_sequence=px.colors.qualitative.Prism,
)

fig_bubble.update_layout(
    margin=dict(l=30, r=30, t=30, b=30),
    height=480,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

st.plotly_chart(fig_bubble, use_container_width=True)

st.write("")

# 2. Sector Median KPI Bar Chart
st.subheader("📊 Sector Median Operational Benchmarks")

median_metrics = [
    ("return_on_equity_pct", "ROE (%)"),
    ("roce_pct", "ROCE (%)"),
    ("net_profit_margin_pct", "Net Profit Margin (%)"),
    ("operating_profit_margin_pct", "OPM (%)"),
]

sec_group = df_universe.groupby("broad_sector")
median_records = []

for sec_name, grp in sec_group:
    row = {"Sector": sec_name}
    for col_key, label in median_metrics:
        s = pd.to_numeric(grp[col_key], errors="coerce").dropna()
        row[label] = round(float(s.median()), 2) if not s.empty else 0.0
    median_records.append(row)

df_medians = pd.DataFrame(median_records).sort_values(by="ROE (%)", ascending=False)

fig_bar = px.bar(
    df_medians,
    x="Sector",
    y=["ROE (%)", "ROCE (%)", "Net Profit Margin (%)", "OPM (%)"],
    barmode="group",
    labels={"value": "Median Percentage (%)", "variable": "Benchmark Metric"},
    color_discrete_sequence=["#1F4E79", "#2CA02C", "#FF7F0E", "#D62728"],
)

fig_bar.update_layout(
    margin=dict(l=30, r=30, t=30, b=30),
    height=400,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
)

st.plotly_chart(fig_bar, use_container_width=True)
