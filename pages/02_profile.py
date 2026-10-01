"""Company Profile Screen — Deep Tear Sheet (Day 23)."""

from __future__ import annotations

import sys
from pathlib import Path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_ratios,
    get_pl,
    get_bs,
    get_cf,
    get_prosandcons,
    get_valuation
)

st.title("🏢 Company Profile & Fundamental Tear Sheet")

# 1. Search Box with Autocomplete
df_comps = get_companies()
ticker_options = [f"{row['ticker']} — {row['company_name']}" for _, row in df_comps.iterrows()]

# Check if ticker passed in query params or session state
default_idx = 0
selected_option = st.selectbox(
    "Search company by ticker or name:",
    options=ticker_options,
    index=default_idx,
    help="Type to search among all 92 Nifty 100 constituents"
)

if not selected_option:
    st.warning("Ticker not found — please try another")
    st.stop()

selected_ticker = selected_option.split(" — ")[0].strip()

# Fetch company metadata
co_match = df_comps[df_comps["ticker"] == selected_ticker]
if co_match.empty:
    st.warning("Ticker not found — please try another")
    st.stop()

co = co_match.iloc[0]

# 2. Company Card
with st.container():
    st.markdown(f"""
    <div style="background-color: #F8F9FA; padding: 20px; border-radius: 8px; border: 1px solid #E0E0E0; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
            <h2 style="margin: 0; color: #1F4E79;">{co['company_name']} ({co['ticker']})</h2>
            <span style="font-size: 14px; font-weight: 600; background: #E1EFFF; color: #1F4E79; padding: 4px 10px; border-radius: 4px;">
                {co['broad_sector']} | {co['sub_sector']}
            </span>
        </div>
        <p style="margin-top: 10px; font-size: 14px; color: #444444; line-height: 1.5;">
            {co['about_company'] if pd.notna(co['about_company']) and str(co['about_company']).strip() else 'Leading constituent company listed in the Nifty 100 index.'}
        </p>
        <div style="font-size: 13px; color: #666;">
            <strong>NSE Profile:</strong> <a href="{co['nse_profile']}" target="_blank">{co['ticker']}</a> | 
            <strong>Website:</strong> <a href="{co['website']}" target="_blank">{co['website']}</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 3. Fetch Ratios for 6 KPI Tiles
df_ratios = get_ratios(selected_ticker)
latest_ratio = df_ratios.iloc[-1] if not df_ratios.empty else {}

roe_val = f"{latest_ratio.get('return_on_equity_pct', 'N/A')}%" if pd.notna(latest_ratio.get('return_on_equity_pct')) else "N/A"
roce_val = f"{latest_ratio.get('roce_pct', 'N/A')}%" if pd.notna(latest_ratio.get('roce_pct')) else "N/A"
npm_val = f"{latest_ratio.get('net_profit_margin_pct', 'N/A')}%" if pd.notna(latest_ratio.get('net_profit_margin_pct')) else "N/A"
de_val = f"{latest_ratio.get('debt_to_equity', 'N/A')}" if pd.notna(latest_ratio.get('debt_to_equity')) else "N/A"
cagr_val = f"{latest_ratio.get('revenue_cagr_5yr', 'N/A')}%" if pd.notna(latest_ratio.get('revenue_cagr_5yr')) else "N/A"
fcf_val = f"₹{latest_ratio.get('free_cash_flow_cr', 'N/A'):,.0f} Cr" if pd.notna(latest_ratio.get('free_cash_flow_cr')) else "N/A"

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Return on Equity", roe_val)
k2.metric("ROCE", roce_val)
k3.metric("Net Profit Margin", npm_val)
k4.metric("Debt-to-Equity", de_val)
k5.metric("5Y Rev CAGR", cagr_val)
k6.metric("Free Cash Flow", fcf_val)

st.write("")

# 4. Fetch 10-Year P&L for Historical Charts
df_pl = get_pl(selected_ticker)

if not df_pl.empty:
    chart_col1, chart_col2 = st.columns(2)

    # Chart 1: 10-Year Bar Chart for Revenue & Net Profit
    with chart_col1:
        st.subheader("📈 10-Year Revenue & Net Profit (₹ Cr)")
        fig_bars = go.Figure()
        fig_bars.add_trace(go.Bar(
            x=df_pl["year"],
            y=df_pl["sales"],
            name="Revenue (Sales)",
            marker_color="#1F4E79",
        ))
        fig_bars.add_trace(go.Bar(
            x=df_pl["year"],
            y=df_pl["net_profit"],
            name="Net Profit (PAT)",
            marker_color="#2CA02C",
        ))
        fig_bars.update_layout(
            barmode="group",
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=350,
        )
        st.plotly_chart(fig_bars, use_container_width=True)

    # Chart 2: ROE & ROCE Dual-Axis Line Chart
    with chart_col2:
        st.subheader("📊 10-Year ROE & ROCE Trend (%)")
        if not df_ratios.empty and "return_on_equity_pct" in df_ratios.columns:
            fig_lines = go.Figure()
            fig_lines.add_trace(go.Scatter(
                x=df_ratios["year"],
                y=df_ratios["return_on_equity_pct"],
                name="ROE (%)",
                mode="lines+markers",
                line=dict(color="#D9534F", width=2.5),
            ))
            fig_lines.add_trace(go.Scatter(
                x=df_ratios["year"],
                y=df_ratios["roce_pct"],
                name="ROCE (%)",
                mode="lines+markers",
                line=dict(color="#0275D8", width=2.5, dash="dot"),
            ))
            fig_lines.update_layout(
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                height=350,
            )
            st.plotly_chart(fig_lines, use_container_width=True)
        else:
            st.info("Ratio history unavailable.")
else:
    st.info("Historical financial data not available for this company.")

st.write("")

# 5. Pros & Cons Qualitative Badges
st.subheader("💡 Qualitative Insights (Pros & Cons)")
pac = get_prosandcons(selected_ticker)
p_col, c_col = st.columns(2)

with p_col:
    st.markdown("##### 🟢 Strengths (Pros)")
    if pac["pros"]:
        for pro in pac["pros"]:
            st.markdown(f"- ✅ **{pro}**")
    else:
        # Dynamic fallback if no manual pros loaded
        if pd.notna(latest_ratio.get("debt_to_equity")) and latest_ratio.get("debt_to_equity") == 0:
            st.markdown("- ✅ **Company is virtually debt free.**")
        if pd.notna(latest_ratio.get("return_on_equity_pct")) and latest_ratio.get("return_on_equity_pct") > 15:
            st.markdown(f"- ✅ **Strong return profile with ROE of {latest_ratio.get('return_on_equity_pct'):.1f}%.**")
        if pd.notna(latest_ratio.get("free_cash_flow_cr")) and latest_ratio.get("free_cash_flow_cr") > 0:
            st.markdown(f"- ✅ **Positive free cash flow generation of ₹{latest_ratio.get('free_cash_flow_cr'):,.0f} Cr.**")
        if not pac["pros"] and not (latest_ratio.get("debt_to_equity") == 0 or latest_ratio.get("return_on_equity_pct", 0) > 15):
            st.write("No qualitative pros recorded.")

with c_col:
    st.markdown("##### 🔴 Weaknesses (Cons)")
    if pac["cons"]:
        for con in pac["cons"]:
            st.markdown(f"- ❌ **{con}**")
    else:
        if pd.notna(latest_ratio.get("debt_to_equity")) and latest_ratio.get("debt_to_equity") > 1.5:
            st.markdown(f"- ❌ **Elevated leverage with D/E ratio of {latest_ratio.get('debt_to_equity'):.2f}.**")
        if pd.notna(latest_ratio.get("free_cash_flow_cr")) and latest_ratio.get("free_cash_flow_cr") < 0:
            st.markdown("- ❌ **Negative free cash flow in the latest fiscal year.**")
        if not pac["cons"] and not (latest_ratio.get("debt_to_equity", 0) > 1.5 or latest_ratio.get("free_cash_flow_cr", 0) < 0):
            st.write("No qualitative cons recorded.")
