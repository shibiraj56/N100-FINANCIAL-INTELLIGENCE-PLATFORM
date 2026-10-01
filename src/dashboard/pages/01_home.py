"""Home Screen — Executive Overview of Nifty 100 (Day 23)."""

from __future__ import annotations

import sys
from pathlib import Path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.db import get_companies, get_home_kpis, get_sectors

st.markdown("""
<style>
    .kpi-card {
        background-color: #F8F9FA;
        border-radius: 8px;
        padding: 16px;
        border-left: 4px solid #1F4E79;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        text-align: center;
    }
    .kpi-title {
        font-size: 13px;
        color: #555555;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 700;
        color: #1F4E79;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ Nifty 100 Financial Intelligence Platform")
st.markdown("Executive macro view and constituent health across the 92 Nifty 100 companies.")

# Sidebar Year Selector
st.sidebar.header("Filter Settings")
available_years = ["2024-03", "2023-03", "2022-03", "2021-03", "2020-03", "2019-03"]
selected_year = st.sidebar.selectbox("Select Fiscal Year", available_years, index=0)

# Fetch Data
kpis = get_home_kpis(year=selected_year)
df_universe = kpis.get("df_universe", pd.DataFrame())

# Top 6 KPI Tiles
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Average ROE</div>
        <div class="kpi-value">{kpis['avg_roe']}%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Median P/E</div>
        <div class="kpi-value">{kpis['median_pe']}x</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Median D/E</div>
        <div class="kpi-value">{kpis['median_de']}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Total Companies</div>
        <div class="kpi-value">{kpis['total_companies']}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Median 5Y Rev CAGR</div>
        <div class="kpi-value">{kpis['median_rev_cagr_5yr']}%</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Debt-Free Blue Chips</div>
        <div class="kpi-value">{kpis['debt_free_count']}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")
st.write("")

# Charts & Tables Layout
c_left, c_right = st.columns([1, 1])

with c_left:
    st.subheader("📊 Sector Composition")
    df_sectors = get_sectors()
    if not df_sectors.empty:
        # Group by broad_sector
        df_sec_summary = df_sectors.groupby("broad_sector", as_index=False)["company_count"].sum()
        df_sec_summary = df_sec_summary.sort_values(by="company_count", ascending=False)

        fig_donut = px.pie(
            df_sec_summary,
            names="broad_sector",
            values="company_count",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Prism,
        )
        fig_donut.update_traces(textposition="inside", textinfo="percent+label")
        fig_donut.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            showlegend=False,
            height=380,
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("No sector data available.")

with c_right:
    st.subheader("⭐ Top 5 Companies by Quality Score")
    if not df_universe.empty and "composite_quality_score" in df_universe.columns:
        df_top5 = df_universe.dropna(subset=["composite_quality_score"]).sort_values(
            by="composite_quality_score", ascending=False
        ).head(5)
        
        # Merge company names
        df_comp = get_companies()
        df_top5_merged = pd.merge(df_top5, df_comp[["ticker", "company_name"]], left_on="company_id", right_on="ticker", how="left")
        
        display_df = df_top5_merged[[
            "company_id", "company_name", "broad_sector", "composite_quality_score", "return_on_equity_pct"
        ]].rename(columns={
            "company_id": "Ticker",
            "company_name": "Company Name",
            "broad_sector": "Sector",
            "composite_quality_score": "Quality Score",
            "return_on_equity_pct": "ROE (%)"
        })
        
        st.dataframe(
            display_df.style.format({
                "Quality Score": "{:.1f}",
                "ROE (%)": "{:.2f}%"
            }),
            use_container_width=True,
            hide_index=True,
            height=380,
        )
    else:
        st.info("No universe data available for this year.")
