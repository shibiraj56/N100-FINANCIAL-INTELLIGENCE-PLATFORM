"""Annual Reports Screen — Repository & Link Health Validation (Day 25)."""

from __future__ import annotations

import sys
from pathlib import Path
root_dir = str(Path(__file__).resolve().parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import pandas as pd
import requests
import streamlit as st

from src.dashboard.utils.db import get_companies, get_annual_reports

st.title("📑 Annual Reports & Regulatory Filings Repository")
st.markdown("Browse, inspect, and download official annual reports and BSE regulatory filings across historical fiscal years.")

df_comps = get_companies()
ticker_options = [f"{row['ticker']} — {row['company_name']}" for _, row in df_comps.iterrows()]

selected_option = st.selectbox(
    "Search company for annual reports:",
    options=ticker_options,
    index=0,
    help="Search filings for any Nifty 100 constituent"
)
selected_ticker = selected_option.split(" — ")[0].strip()

# Fetch reports
df_reports = get_annual_reports(selected_ticker)

@st.cache_data(ttl=3600)
def check_report_url_status(url: str) -> bool:
    """Fast HEAD check to verify URL validity with 1.5s timeout."""
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return False
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.head(url, headers=headers, timeout=1.5, allow_redirects=True)
        return resp.status_code < 400
    except Exception:
        return False

if df_reports.empty:
    st.info(f"No annual reports archived for `{selected_ticker}`.")
else:
    st.subheader(f"📂 Available Annual Reports for {selected_ticker} ({len(df_reports)} filings)")

    report_cards = []
    for _, row in df_reports.iterrows():
        yr = row["year"]
        url = row["annual_report"]

        is_valid = check_report_url_status(url)

        if is_valid:
            status_html = f'<a href="{url}" target="_blank" style="text-decoration: none; background: #2CA02C; color: white; padding: 6px 14px; border-radius: 4px; font-weight: bold; font-size: 13px;">📥 Download PDF</a>'
        else:
            status_html = '<span style="background: #D9534F; color: white; padding: 6px 14px; border-radius: 4px; font-weight: bold; font-size: 13px;">⚠️ Report unavailable</span>'

        st.markdown(f"""
        <div style="background-color: #F8F9FA; padding: 14px 20px; border-radius: 6px; border: 1px solid #E0E0E0; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong style="font-size: 16px; color: #1F4E79;">Fiscal Year {yr}</strong>
                <div style="font-size: 12px; color: #777; margin-top: 4px;">{url[:80]}...</div>
            </div>
            <div>
                {status_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
