"""N100 Financial Intelligence Platform — Streamlit Main Application (Day 22).

Entry point for the 8-screen institutional analytics dashboard.
Configures wide layout, expanded sidebar, custom typography, and navigation routing.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

# Ensure repository root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import streamlit as st

# 1. Page Configuration
st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Custom Styling
st.markdown("""
<style>
    /* Global layout tweaks */
    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
    }
    /* Sidebar header branding */
    .sidebar-brand {
        font-size: 18px;
        font-weight: 700;
        color: #1F4E79;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# 3. Sidebar Branding
st.sidebar.markdown("""
<div style="text-align: center; padding: 10px 0 20px 0;">
    <h2 style="color: #1F4E79; margin: 0;">🏛️ N100 PLATFORM</h2>
    <span style="font-size: 12px; color: #666;">Institutional Financial Intelligence</span>
</div>
""", unsafe_allow_html=True)

# 4. Streamlit Multi-Page Navigation Routing
# Resolves paths relative to repository root
pages_dict = {
    "Macro Overview": [
        st.Page("pages/01_home.py", title="Home Overview", icon="🏠", default=True),
        st.Page("pages/02_profile.py", title="Company Profile", icon="🏢"),
    ],
    "Screening & Peers": [
        st.Page("pages/03_screener.py", title="Stock Screener", icon="🔍"),
        st.Page("pages/04_peers.py", title="Peer Comparison", icon="👥"),
    ],
    "Deep Dive Analytics": [
        st.Page("pages/05_trends.py", title="Trend Analysis", icon="📈"),
        st.Page("pages/06_sectors.py", title="Sector Analysis", icon="🏭"),
        st.Page("pages/07_capital.py", title="Capital Allocation", icon="💰"),
        st.Page("pages/08_reports.py", title="Annual Reports", icon="📑"),
    ],
}

pg = st.navigation(pages_dict)
pg.run()
