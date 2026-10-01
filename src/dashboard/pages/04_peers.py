"""Peer Comparison Screen — Intra-Group Benchmarking & Radar (Day 24)."""

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

from src.analytics.peer import PeerEngine, RADAR_AXES
from src.dashboard.utils.db import get_peers, get_ratios, get_companies

st.title("👥 Intra-Group Peer Comparison & Radar Analysis")
st.markdown("Benchmark companies against industry peers with 8-axis polar radar overlays and side-by-side KPI matrices.")

# 1. Peer Group Selector
df_all_peers = get_peers()
group_names = sorted(df_all_peers["peer_group_name"].unique().tolist())

selected_group = st.selectbox("Select Peer Group:", group_names, index=0)
df_group_peers = get_peers(selected_group)

# 2. Company Selector within Peer Group
company_options = df_group_peers["company_id"].tolist()
selected_ticker = st.selectbox("Select Company to Overlay against Peer Group:", company_options, index=0)

# Fetch ratio data for all companies in the peer group
peer_tickers = df_group_peers["company_id"].tolist()

@st.cache_data(ttl=600)
def load_peer_kpis(tickers: tuple):
    engine = PeerEngine()
    _, df_r = engine.load_peer_universe(year="2024-03")
    return df_r[df_r["company_id"].isin(tickers)]

df_group_ratios = load_peer_kpis(tuple(peer_tickers))
df_merged = pd.merge(df_group_peers, df_group_ratios, on="company_id", how="left")

# 3. Radar Chart (Plotly Scatterpolar)
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader(f"🎯 8-Axis Polar Radar: {selected_ticker} vs {selected_group} Average")
    
    # Calculate company normalized values and group average
    categories = [axis[0] for axis in RADAR_AXES]
    comp_vals = []
    group_avg_vals = []

    comp_row = df_merged[df_merged["company_id"] == selected_ticker]
    has_comp = not comp_row.empty

    for axis_label, raw_col, is_inverse, default_max in RADAR_AXES:
        # Group series
        s = pd.to_numeric(df_merged[raw_col], errors="coerce").dropna()
        max_val = max(s.max() if not s.empty else default_max, default_max)

        # Company normalized (0-100)
        c_val = comp_row.iloc[0].get(raw_col) if has_comp else None
        if pd.notna(c_val):
            val_f = float(c_val)
            norm = (val_f / max_val * 100.0) if max_val > 0 else 50.0
            norm = max(0.0, min(100.0, norm))
            if is_inverse:
                norm = 100.0 - norm
            comp_vals.append(round(norm, 1))
        else:
            comp_vals.append(50.0)

        # Group average normalized
        if not s.empty:
            avg_raw = s.mean()
            norm_avg = (avg_raw / max_val * 100.0) if max_val > 0 else 50.0
            norm_avg = max(0.0, min(100.0, norm_avg))
            if is_inverse:
                norm_avg = 100.0 - norm_avg
            group_avg_vals.append(round(norm_avg, 1))
        else:
            group_avg_vals.append(50.0)

    # Close the radar loop
    radar_cats = categories + [categories[0]]
    comp_vals_loop = comp_vals + [comp_vals[0]]
    group_avg_loop = group_avg_vals + [group_avg_vals[0]]

    fig_radar = go.Figure()
    # Company trace
    fig_radar.add_trace(go.Scatterpolar(
        r=comp_vals_loop,
        theta=radar_cats,
        fill="toself",
        name=selected_ticker,
        line=dict(color="#1F4E79", width=2.5),
        fillcolor="rgba(31, 78, 121, 0.35)",
    ))
    # Peer Average trace
    fig_radar.add_trace(go.Scatterpolar(
        r=group_avg_loop,
        theta=radar_cats,
        name=f"{selected_group} Avg",
        line=dict(color="#D9534F", width=2, dash="dash"),
    ))

    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
        ),
        margin=dict(l=40, r=40, t=30, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
        height=380,
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with col_right:
    st.subheader(f"📋 Constituent Overview: {selected_group}")
    benchmark_co = df_group_peers[df_group_peers["is_benchmark"] == 1]
    bench_name = benchmark_co.iloc[0]["company_id"] if not benchmark_co.empty else "N/A"
    st.info(f"🏆 **Benchmark Company:** `{bench_name}` (highest market cap in cluster)")
    
    st.markdown("""
    - **Radar Axes Normalized to 0–100**:
      - Profitability: ROE, ROCE, NPM
      - Risk & Capital: D/E Score (inverted), FCF Score, Quality Score
      - Growth: 5Y PAT CAGR, 5Y Revenue CAGR
    - **Benchmark Row**: Highlighted in gold in the table below.
    """)

st.write("")

# 4. Side-by-Side KPI Table with Benchmark Highlighting
st.subheader("📊 Side-by-Side Financial Comparison")

kpi_cols = [
    "company_id", "company_name_x", "is_benchmark",
    "composite_quality_score", "return_on_equity_pct", "roce_pct",
    "net_profit_margin_pct", "debt_to_equity", "free_cash_flow_cr",
    "revenue_cagr_5yr", "pe_ratio"
]
available_kpi_cols = [c for c in kpi_cols if c in df_merged.columns]

table_df = df_merged[available_kpi_cols].copy()
table_df = table_df.rename(columns={
    "company_id": "Ticker",
    "company_name_x": "Company Name",
    "composite_quality_score": "Quality Score",
    "return_on_equity_pct": "ROE (%)",
    "roce_pct": "ROCE (%)",
    "net_profit_margin_pct": "NPM (%)",
    "debt_to_equity": "D/E",
    "free_cash_flow_cr": "FCF (₹ Cr)",
    "revenue_cagr_5yr": "5Y Rev CAGR (%)",
    "pe_ratio": "P/E"
})

def highlight_benchmark(row):
    if row.get("is_benchmark") == 1:
        return ["background-color: #FFE599; font-weight: bold;"] * len(row)
    return [""] * len(row)

styled_table = table_df.drop(columns=["is_benchmark"], errors="ignore").style.apply(
    highlight_benchmark, axis=1
).format({
    "Quality Score": "{:.1f}",
    "ROE (%)": "{:.1f}%",
    "ROCE (%)": "{:.1f}%",
    "NPM (%)": "{:.1f}%",
    "D/E": "{:.2f}",
    "FCF (₹ Cr)": "₹{:,.0f}",
    "5Y Rev CAGR (%)": "{:.1f}%",
    "P/E": "{:.1f}x",
}, na_rep="—")

st.dataframe(styled_table, use_container_width=True, hide_index=True)
