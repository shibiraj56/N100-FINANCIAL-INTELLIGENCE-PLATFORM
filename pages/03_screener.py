"""Screener Screen — Multi-Criteria Filter Engine (Day 24)."""

from __future__ import annotations

import io
import sys
from pathlib import Path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd
import streamlit as st

from src.screener.engine import ScreenerEngine

st.title("🔍 Multi-Criteria Financial Screener")
st.markdown("Filter and discover Nifty 100 opportunities using custom slider thresholds or canonical investment presets.")

# Initialize Screener Engine
@st.cache_resource
def get_screener():
    return ScreenerEngine()

engine = get_screener()
df_universe = engine.get_universe_data(year="2024-03")

# Preset Threshold Configurations
PRESETS = {
    "quality": {
        "roe_min": 15.0, "de_max": 1.0, "fcf_min": 0.0, "rev_cagr_min": 10.0,
        "pat_cagr_min": 0.0, "opm_min": 0.0, "pe_max": 100.0, "pb_max": 25.0,
        "div_yield_min": 0.0, "icr_min": 0.0
    },
    "value": {
        "roe_min": 0.0, "de_max": 2.0, "fcf_min": -5000.0, "rev_cagr_min": 0.0,
        "pat_cagr_min": 0.0, "opm_min": 0.0, "pe_max": 25.0, "pb_max": 5.0,
        "div_yield_min": 1.0, "icr_min": 0.0
    },
    "growth": {
        "roe_min": 0.0, "de_max": 2.0, "fcf_min": -5000.0, "rev_cagr_min": 15.0,
        "pat_cagr_min": 20.0, "opm_min": 0.0, "pe_max": 100.0, "pb_max": 25.0,
        "div_yield_min": 0.0, "icr_min": 0.0
    },
    "dividend": {
        "roe_min": 0.0, "de_max": 5.0, "fcf_min": 0.0, "rev_cagr_min": 0.0,
        "pat_cagr_min": 0.0, "opm_min": 0.0, "pe_max": 100.0, "pb_max": 25.0,
        "div_yield_min": 2.0, "icr_min": 0.0
    },
    "debt_free": {
        "roe_min": 12.0, "de_max": 0.0, "fcf_min": -5000.0, "rev_cagr_min": 0.0,
        "pat_cagr_min": 0.0, "opm_min": 0.0, "pe_max": 100.0, "pb_max": 25.0,
        "div_yield_min": 0.0, "icr_min": 0.0
    },
    "turnaround": {
        "roe_min": 0.0, "de_max": 5.0, "fcf_min": 0.0, "rev_cagr_min": 10.0,
        "pat_cagr_min": 0.0, "opm_min": 0.0, "pe_max": 100.0, "pb_max": 25.0,
        "div_yield_min": 0.0, "icr_min": 0.0
    },
}

# Ensure session state defaults
default_vals = {
    "roe_min": 0.0, "de_max": 5.0, "fcf_min": -5000.0, "rev_cagr_min": 0.0,
    "pat_cagr_min": 0.0, "opm_min": 0.0, "pe_max": 100.0, "pb_max": 25.0,
    "div_yield_min": 0.0, "icr_min": 0.0
}
for k, v in default_vals.items():
    if k not in st.session_state:
        st.session_state[k] = v

def apply_preset(preset_key: str):
    preset = PRESETS[preset_key]
    for k, v in preset.items():
        st.session_state[k] = v

# Quick-Action Preset Buttons
st.markdown("##### ⚡ Quick-Action Canonical Presets")
b1, b2, b3, b4, b5, b6 = st.columns(6)
with b1:
    if st.button("🌟 Quality Compounder", use_container_width=True):
        apply_preset("quality")
with b2:
    if st.button("💎 Value Pick", use_container_width=True):
        apply_preset("value")
with b3:
    if st.button("🚀 Growth Accelerator", use_container_width=True):
        apply_preset("growth")
with b4:
    if st.button("💰 Dividend Champion", use_container_width=True):
        apply_preset("dividend")
with b5:
    if st.button("🛡️ Debt-Free Blue Chip", use_container_width=True):
        apply_preset("debt_free")
with b6:
    if st.button("🔄 Turnaround Watch", use_container_width=True):
        apply_preset("turnaround")

st.write("")

# Sidebar Sliders (10 metrics)
st.sidebar.header("Filter Criteria (10 Metrics)")

roe_val = st.sidebar.slider("Minimum ROE (%)", 0.0, 50.0, float(st.session_state["roe_min"]), 1.0, key="roe_min")
de_val = st.sidebar.slider("Maximum D/E Ratio", 0.0, 5.0, float(st.session_state["de_max"]), 0.1, key="de_max")
fcf_val = st.sidebar.slider("Minimum FCF (₹ Cr)", -5000.0, 25000.0, float(st.session_state["fcf_min"]), 500.0, key="fcf_min")
rev_cagr_val = st.sidebar.slider("Minimum 5Y Rev CAGR (%)", 0.0, 30.0, float(st.session_state["rev_cagr_min"]), 1.0, key="rev_cagr_min")
pat_cagr_val = st.sidebar.slider("Minimum 5Y PAT CAGR (%)", 0.0, 40.0, float(st.session_state["pat_cagr_min"]), 1.0, key="pat_cagr_min")
opm_val = st.sidebar.slider("Minimum OPM (%)", 0.0, 50.0, float(st.session_state["opm_min"]), 1.0, key="opm_min")
pe_val = st.sidebar.slider("Maximum P/E Ratio", 5.0, 100.0, float(st.session_state["pe_max"]), 5.0, key="pe_max")
pb_val = st.sidebar.slider("Maximum P/B Ratio", 1.0, 25.0, float(st.session_state["pb_max"]), 0.5, key="pb_max")
div_val = st.sidebar.slider("Minimum Dividend Yield (%)", 0.0, 10.0, float(st.session_state["div_yield_min"]), 0.5, key="div_yield_min")
icr_val = st.sidebar.slider("Minimum Interest Coverage (ICR)", 0.0, 20.0, float(st.session_state["icr_min"]), 0.5, key="icr_min")

# Apply Filters
active_filters = {
    "roe_min": roe_val if roe_val > 0 else None,
    "de_max": de_val,
    "fcf_min": fcf_val if fcf_val > -5000 else None,
    "rev_cagr_5yr_min": rev_cagr_val if rev_cagr_val > 0 else None,
    "pat_cagr_5yr_min": pat_cagr_val if pat_cagr_val > 0 else None,
    "opm_min": opm_val if opm_val > 0 else None,
    "pe_max": pe_val if pe_val < 100 else None,
    "pb_max": pb_val if pb_val < 25 else None,
    "div_yield_min": div_val if div_val > 0 else None,
    "icr_min": icr_val if icr_val > 0 else None,
}

filtered_df = engine.apply_filters(df_universe, active_filters)
filtered_df = filtered_df.sort_values(by="composite_quality_score", ascending=False)

# Results Counter and Actions
count_col, dl_col = st.columns([3, 1])
with count_col:
    st.markdown(f"#### 🎯 **{len(filtered_df)} companies** match your screening criteria")

with dl_col:
    csv_data = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download CSV",
        data=csv_data,
        file_name="screener_filtered_results.csv",
        mime="text/csv",
        use_container_width=True,
    )

# Display Table with Essential Columns
display_cols = [
    "company_id", "company_name", "broad_sector", "composite_quality_score",
    "return_on_equity_pct", "debt_to_equity", "free_cash_flow_cr",
    "revenue_cagr_5yr", "pat_cagr_5yr", "operating_profit_margin_pct",
    "pe_ratio", "pb_ratio", "dividend_yield_pct", "interest_coverage"
]

renamed_cols = {
    "company_id": "Ticker",
    "company_name": "Company Name",
    "broad_sector": "Sector",
    "composite_quality_score": "Quality Score",
    "return_on_equity_pct": "ROE (%)",
    "debt_to_equity": "D/E",
    "free_cash_flow_cr": "FCF (₹ Cr)",
    "revenue_cagr_5yr": "5Y Rev CAGR (%)",
    "pat_cagr_5yr": "5Y PAT CAGR (%)",
    "operating_profit_margin_pct": "OPM (%)",
    "pe_ratio": "P/E",
    "pb_ratio": "P/B",
    "dividend_yield_pct": "Div Yield (%)",
    "interest_coverage": "ICR"
}

table_view = filtered_df[display_cols].rename(columns=renamed_cols)

st.dataframe(
    table_view.style.format({
        "Quality Score": "{:.1f}",
        "ROE (%)": "{:.1f}%",
        "D/E": "{:.2f}",
        "FCF (₹ Cr)": "₹{:,.0f}",
        "5Y Rev CAGR (%)": "{:.1f}%",
        "5Y PAT CAGR (%)": "{:.1f}%",
        "OPM (%)": "{:.1f}%",
        "P/E": "{:.1f}x",
        "P/B": "{:.2f}x",
        "Div Yield (%)": "{:.2f}%",
        "ICR": "{:.2f}"
    }, na_rep="—"),
    use_container_width=True,
    hide_index=True,
    height=450,
)
