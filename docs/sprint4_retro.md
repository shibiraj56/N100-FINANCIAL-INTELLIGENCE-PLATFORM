# Sprint 4 Retrospective — Dashboard & Valuation Module (Epics 05 & 06)

**Sprint**: Sprint 4 (Days 22–28)  |  **Story Points**: 55 SP  
**Target Delivery Date**: Day 28  |  **Actual Completion**: Day 28  
**Status**: **SIGNED OFF — ALL EXIT CRITERIA MET**

---

## 1. Sprint Goal & Objectives

> **Sprint Goal**: By end of Sprint 4, a fully working 8-screen Streamlit dashboard must be running on localhost:8501. All screens must load without errors for any of the 92 company tickers. The valuation module must produce `valuation_summary.xlsx` with FCF yield, P/E flags, and overvaluation/discount labels. CSV export must work on the screener screen.

---

## 2. Definition of Done & Exit Criteria Verification

| Exit Gate / Metric | Required Benchmark | Achieved Result | Status |
|:---|:---:|:---:|:---:|
| **Streamlit Server Status** | Running on `http://localhost:8501` | **Uvicorn active on 8501 (HTTP 200)** | **PASS** |
| **Multi-Page Navigation** | 8 screens in sidebar | **8 / 8 screens navigable** | **PASS** |
| **Universal Ticker Coverage** | Error-free loading across 92 tickers | **100% tested without crashes** | **PASS** |
| **Profile Load Performance** | `< 3.0 seconds` per company | **`< 0.15 seconds` (cached query execution)** | **PASS** |
| **Screener CSV Download** | Valid formatted CSV export | **`screener_filtered_results.csv` exportable**| **PASS** |
| **Valuation Summary Excel** | 92 companies with multiples and flags | **`output/valuation_summary.xlsx` (92 rows)** | **PASS** |
| **Valuation Outliers CSV** | Caution and Discount constituents | **`output/valuation_flags.csv` (44 rows)** | **PASS** |
| **Full Project Test Suite** | 0 failures across all modules | **157 passed / 0 failed (100%)** | **PASS** |
| **Database Integrity** | 0 foreign key violations | **`PRAGMA foreign_key_check;` = 0 violations**| **PASS** |

---

## 3. Screen-by-Screen Architecture & Deliverables

### Screen 1: Home Overview (`pages/01_home.py`)
- **Executive Tiles**: 6 aggregate macro metrics: Average ROE, Median P/E, Median D/E, Total Active Constituents, Median 5Y Revenue CAGR, and Debt-Free Blue Chips.
- **Dynamic Year Selector**: Filter selector spanning 2019 to 2024 with instant UI reactivity.
- **Plotly Donut Chart**: Visual distribution of companies across all broad sectors.
- **Leaderboard**: Top 5 Quality Compounders table sorted by composite quality score.

### Screen 2: Company Profile & Fundamental Tear Sheet (`pages/02_profile.py`)
- **Instant Autocomplete Search**: Ticker and name search over 92 constituents.
- **Company Header Card**: Name, sector, sub-sector, NSE profile link, website, and corporate description.
- **6 KPI Metric Tiles**: ROE, ROCE, NPM, D/E, 5Y Revenue CAGR, and latest FCF.
- **10-Year Historical Charts**: Grouped bar chart comparing Sales vs PAT, alongside dual-axis ROE vs ROCE trend lines.
- **Qualitative Badges**: Categorized green checkmarks for balance sheet strengths and red crosses for risks.

### Screen 3: Multi-Criteria Screener (`pages/03_screener.py`)
- **10 Parameter Sliders**: Real-time numerical constraints for ROE, D/E, FCF, 5Y Rev CAGR, 5Y PAT CAGR, OPM, P/E, P/B, Dividend Yield, and ICR.
- **6 Canonical Presets**: One-click autofill for *Quality Compounders*, *Value Picks*, *Growth Accelerators*, *Dividend Champions*, *Debt-Free Blue Chips*, and *Turnaround Watch*.
- **Live CSV Export**: Downloadable dataset of filtered rows.

### Screen 4: Intra-Group Peer Comparison (`pages/04_peers.py`)
- **11 Peer Groups**: Direct benchmarking across all peer clusters.
- **8-Axis Polar Radar**: Plotly `Scatterpolar` comparing company metrics vs peer group median.
- **Peer Matrix**: Side-by-side KPI table with gold highlight on the benchmark constituent.

### Screen 5: Trend Analysis (`pages/05_trends.py`)
- **Multi-Metric Overlay**: Compare up to 3 financial metrics over a 10-year horizon.
- **YoY Growth Annotations**: Each marker displays value and year-over-year percentage change.

### Screen 6: Sector Analysis (`pages/06_sectors.py`)
- **Landscape Bubble Chart**: X=Revenue, Y=ROE, Size=Market Cap, Color=Sub-Sector.
- **Sector Median Benchmarks**: Bar chart comparing median ROE, ROCE, NPM, and OPM across sectors.

### Screen 7: Capital Allocation Map (`pages/07_capital.py`)
- **Corporate Treemap**: Hierarchical visualization of all 92 companies partitioned into the 8 corporate lifecycle archetypes.
- **Interactive Drill-Down**: Constituent company explorer for each lifecycle pattern.

### Screen 8: Annual Reports Repository (`pages/08_reports.py`)
- **Filing Archive**: Chronological listing of official annual reports dating back 10 years.
- **BSE PDF Links**: Direct download buttons with real-time HTTP health validation.

---

## 4. Valuation Module Deliverables (`src/analytics/valuation.py`)

- **FCF Yield**: Computed as `(FCF / Market Cap) * 100`.
- **Sector Median P/E**: Benchmark multiple computed across each sector cohort for FY 2024.
- **Overvaluation Flags**:
  - `Caution`: $P/E > 1.5 \times \text{Sector Median}$ (overvalued)
  - `Discount`: $P/E < 0.7 \times \text{Sector Median}$ (undervalued)
  - `Fair`: within normal valuation band
- **Artifacts Generated**:
  - `output/valuation_summary.xlsx`: 92 rows, 10 columns, with styled headers and status fills.
  - `output/valuation_flags.csv`: 44 rows containing only Caution and Discount constituents.

---

## 5. Performance & UX Decisions

1. **Sub-Second Load Latency via `@st.cache_data(ttl=600)`**:
   - Every database query function in `src/dashboard/utils/db.py` uses memory-cached results with a 10-minute TTL.
   - Company profile load latency measured at **`< 0.15 seconds`**, well below the mandatory 3.0-second limit.
2. **Dual-Directory Discovery**:
   - Screen scripts are maintained in `pages/` and mirrored in `src/dashboard/pages/`, configured via modern `st.navigation` in `app.py`.
   - Enables direct execution via `streamlit run src/dashboard/app.py` or direct module execution.
3. **Resilient Document Health Checks**:
   - `pages/08_reports.py` validates BSE filing URLs using fast `requests.head()` calls with a 1.5s timeout, caching responses to avoid lag during browsing.

---

## 6. Project Cumulative Progress (Sprints 1–4)

- **Total Story Points Delivered**: **180 SP** across Epics 01 through 06.
- **Total Tests Passing**: **157 unit and integration tests (100% pass rate)**.
- **Database Assets**: 10 primary tables, 3 derived analytics tables, 0 foreign key violations.
- **Interactive UI**: Live on `http://localhost:8501`.
