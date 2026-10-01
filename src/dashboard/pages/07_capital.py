"""Capital Allocation Map Screen — Treemap & Lifecycle Analysis (Day 25)."""

from __future__ import annotations

import sys
from pathlib import Path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import get_capital_allocation

st.title("💰 Capital Allocation & Lifecycle Map")
st.markdown("Visualise all 92 Nifty 100 companies segmented across the 8 canonical capital allocation lifecycle archetypes.")

df_ca = get_capital_allocation()

if df_ca.empty:
    st.warning("Capital allocation data unavailable.")
    st.stop()

# 1. Summary Metrics across 8 patterns
st.subheader("🗺️ Universal Corporate Capital Allocation Treemap")
st.caption("Tile Size: Market Capitalisation (₹ Cr) | Hierarchy: Pattern Archetype → Broad Sector → Company")

# Ensure valid positive sizes for treemap
plot_ca = df_ca.copy()
plot_ca["market_cap_clean"] = plot_ca["market_cap_crore"].fillna(1000).clip(lower=500)

fig_treemap = px.treemap(
    plot_ca,
    path=["pattern_label", "broad_sector", "company_id"],
    values="market_cap_clean",
    color="pattern_label",
    hover_name="company_name",
    hover_data={
        "pattern_label": True,
        "broad_sector": True,
        "fcf_cr": ":,.0f",
        "market_cap_clean": False,
        "market_cap_crore": ":,.0f",
    },
    color_discrete_sequence=px.colors.qualitative.Safe,
)

fig_treemap.update_layout(
    margin=dict(l=10, r=10, t=20, b=10),
    height=520,
)

st.plotly_chart(fig_treemap, use_container_width=True)

st.write("")

# 2. Interactive Pattern Drill-Down
st.subheader("🔍 Archetype Drill-Down & Constituent Explorer")

all_patterns = sorted(df_ca["pattern_label"].dropna().unique().tolist())
selected_pattern = st.selectbox(
    "Select Pattern Archetype to inspect constituent companies:",
    options=["All Archetypes"] + all_patterns,
    index=0
)

if selected_pattern != "All Archetypes":
    subset_df = df_ca[df_ca["pattern_label"] == selected_pattern].copy()
else:
    subset_df = df_ca.copy()

st.markdown(f"**Showing {len(subset_df)} companies** in `{selected_pattern}`:")

display_table = subset_df[[
    "company_id", "company_name", "broad_sector", "pattern_label",
    "cfo_cr", "cfi_cr", "cff_cr", "fcf_cr", "market_cap_crore"
]].rename(columns={
    "company_id": "Ticker",
    "company_name": "Company Name",
    "broad_sector": "Sector",
    "pattern_label": "Lifecycle Archetype",
    "cfo_cr": "CFO (₹ Cr)",
    "cfi_cr": "CFI (₹ Cr)",
    "cff_cr": "CFF (₹ Cr)",
    "fcf_cr": "FCF (₹ Cr)",
    "market_cap_crore": "Market Cap (₹ Cr)"
})

st.dataframe(
    display_table.style.format({
        "CFO (₹ Cr)": "₹{:,.0f}",
        "CFI (₹ Cr)": "₹{:,.0f}",
        "CFF (₹ Cr)": "₹{:,.0f}",
        "FCF (₹ Cr)": "₹{:,.0f}",
        "Market Cap (₹ Cr)": "₹{:,.0f}"
    }, na_rep="—"),
    use_container_width=True,
    hide_index=True,
    height=400,
)
