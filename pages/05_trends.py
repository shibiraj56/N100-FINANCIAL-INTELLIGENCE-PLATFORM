"""Trend Analysis Screen — Multi-Metric 10-Year Historical Trends (Day 25)."""

from __future__ import annotations

import sys
from pathlib import Path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_companies, get_pl, get_ratios

st.title("📈 10-Year Historical Financial Trend Analysis")
st.markdown("Analyze longitudinal performance and structural inflections with multi-metric overlays and YoY percentage annotations.")

df_comps = get_companies()
ticker_options = [f"{row['ticker']} — {row['company_name']}" for _, row in df_comps.iterrows()]

col_search, col_metrics = st.columns([1, 2])

with col_search:
    selected_option = st.selectbox(
        "Select Company:",
        options=ticker_options,
        index=0,
        help="Search among all 92 companies"
    )
    selected_ticker = selected_option.split(" — ")[0].strip()

# Metric definitions: mapping label -> (table, column_name, unit)
METRIC_REGISTRY = {
    "Revenue / Sales (₹ Cr)": ("pl", "sales", "₹ Cr"),
    "Net Profit / PAT (₹ Cr)": ("pl", "net_profit", "₹ Cr"),
    "Operating Profit / EBITDA (₹ Cr)": ("pl", "operating_profit", "₹ Cr"),
    "Return on Equity / ROE (%)": ("ratios", "return_on_equity_pct", "%"),
    "ROCE (%)": ("ratios", "roce_pct", "%"),
    "Operating Margin / OPM (%)": ("ratios", "operating_profit_margin_pct", "%"),
    "Debt-to-Equity (D/E)": ("ratios", "debt_to_equity", "x"),
    "Free Cash Flow (₹ Cr)": ("ratios", "free_cash_flow_cr", "₹ Cr"),
    "Asset Turnover": ("ratios", "asset_turnover", "x"),
}

with col_metrics:
    selected_metrics = st.multiselect(
        "Select up to 3 metrics to overlay:",
        options=list(METRIC_REGISTRY.keys()),
        default=["Revenue / Sales (₹ Cr)", "Net Profit / PAT (₹ Cr)"],
        max_selections=3,
    )

if not selected_metrics:
    st.warning("Please select at least one metric to display trends.")
    st.stop()

# Fetch historical data
df_pl = get_pl(selected_ticker)
df_ratios = get_ratios(selected_ticker)

# Merge datasets on year
df_merged = pd.merge(df_pl, df_ratios, on=["company_id", "year"], how="outer", suffixes=("_pl", "_ratios"))
df_merged = df_merged.sort_values(by="year").reset_index(drop=True)

if df_merged.empty:
    st.info("No historical financial data available for this ticker.")
    st.stop()

# Build Trend Line Chart with YoY Annotations
fig = go.Figure()
colors = ["#1F4E79", "#2CA02C", "#D9534F"]

for idx, metric_label in enumerate(selected_metrics):
    src_tbl, col_name, unit = METRIC_REGISTRY[metric_label]
    
    # Resolve column name in merged dataframe
    target_col = col_name
    if target_col not in df_merged.columns:
        if f"{col_name}_pl" in df_merged.columns:
            target_col = f"{col_name}_pl"
        elif f"{col_name}_ratios" in df_merged.columns:
            target_col = f"{col_name}_ratios"

    if target_col not in df_merged.columns:
        continue

    series = pd.to_numeric(df_merged[target_col], errors="coerce")
    years = df_merged["year"]

    # Calculate YoY change (%)
    yoy_pct = series.pct_change() * 100.0

    # Custom text annotations: Value + (YoY %)
    text_labels = []
    for i, (val, yoy) in enumerate(zip(series, yoy_pct)):
        if pd.isna(val):
            text_labels.append("")
        elif i == 0 or pd.isna(yoy):
            text_labels.append(f"{val:,.1f} {unit}")
        else:
            sign = "+" if yoy > 0 else ""
            text_labels.append(f"{val:,.1f}<br>({sign}{yoy:.1f}%)")

    fig.add_trace(go.Scatter(
        x=years,
        y=series,
        name=metric_label,
        mode="lines+markers+text",
        text=text_labels,
        textposition="top center",
        line=dict(color=colors[idx % len(colors)], width=2.5),
        marker=dict(size=8),
    ))

fig.update_layout(
    title=f"10-Year Trajectory for {selected_ticker}",
    xaxis_title="Fiscal Year",
    yaxis_title="Metric Value",
    margin=dict(l=40, r=40, t=50, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
    height=500,
)

st.plotly_chart(fig, use_container_width=True)

# Historical Data Table
with st.expander("🔍 View Raw Historical Data"):
    st.dataframe(df_merged[["year"] + [c for c in df_merged.columns if any(m[1] in c for m in METRIC_REGISTRY.values())]], use_container_width=True)
