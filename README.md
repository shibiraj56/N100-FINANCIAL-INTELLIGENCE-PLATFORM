# N100 Financial Intelligence Platform

An institutional-grade equity research and financial analytics platform covering all 92 constituents of the Nifty 100 universe. Built with Python, SQLite, Plotly, and Streamlit.

---

## 1. Quickstart & Installation

### Prerequisites
- Python 3.12+
- Virtual environment (`venv`)

### Installation
```bash
# Clone the repository and navigate to the project directory
cd "c:\blue stock\N100 FINANCIAL INTELLIGENCE PLATFORM"

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### Launch the Streamlit Dashboard
```bash
streamlit run src/dashboard/app.py
```
The application will start locally on: **`http://localhost:8501`**.

---

## 2. Interactive Dashboard Guide (8 Screens)

The dashboard provides institutional-grade analytical tooling across 8 multi-page modules:

### 🏠 Screen 1: Home Overview (`pages/01_home.py`)
- **Macro Health Tiles**: Real-time aggregate KPIs across the Nifty 100 universe (Average ROE, Median P/E, Median D/E, Total Active Constituents, Median 5Y Revenue CAGR, and Debt-Free Blue Chips count).
- **Fiscal Year Selector**: Dynamically update all universe metrics from FY 2019 to FY 2024 via sidebar dropdown.
- **Sector Donut Chart**: Interactive Plotly breakdown of constituent company distribution across broad sectors.
- **Top 5 Quality Compounders**: Live leaderboard of top-performing stocks ranked by Composite Quality Score.

### 🏢 Screen 2: Company Profile & Fundamental Tear Sheet (`pages/02_profile.py`)
- **Instant Autocomplete Search**: Search any of the 92 constituents by ticker or company name.
- **Corporate Metadata Card**: Company description, broad sector, sub-sector, NSE profile link, and official website.
- **6 Critical KPI Tiles**: ROE, ROCE, Net Profit Margin, Debt-to-Equity, 5-Year Revenue CAGR, and latest Free Cash Flow.
- **10-Year Historical Charts**: Grouped bar chart comparing Sales vs Net Profit, alongside a dual-axis ROE vs ROCE trend line.
- **Qualitative Insights**: Categorized positive strengths (green badges) and corporate risks/weaknesses (red badges).

### 🔍 Screen 3: Multi-Criteria Screener (`pages/03_screener.py`)
- **10 Parameter Sliders**: Customize quantitative thresholds for ROE, D/E, FCF, 5Y Revenue CAGR, 5Y PAT CAGR, OPM, P/E, P/B, Dividend Yield, and ICR.
- **6 Quick-Action Canonical Presets**: One-click autofill for *Quality Compounders*, *Value Picks*, *Growth Accelerators*, *Dividend Champions*, *Debt-Free Blue Chips*, and *Turnaround Watch*.
- **Sector-Relative Scoring**: Normalized P10/P90 scoring within sector cohorts.
- **Live CSV Export**: Download filtered results with a single click (`screener_filtered_results.csv`).

### 👥 Screen 4: Intra-Group Peer Comparison (`pages/04_peers.py`)
- **11 Peer Clusters**: Direct benchmarking across Automobiles, Private Banks, PSUs, FMCG, IT Services, Oil & Gas, Pharma, Power, Steel, Life Insurance, and Consumer Finance.
- **8-Axis Polar Radar Chart**: Plotly `Scatterpolar` visual overlay comparing a selected company against its peer group average across profitability, leverage, growth, and cash flow axes.
- **Side-by-Side Matrix**: Comprehensive financial comparison table with the benchmark market leader highlighted in gold.

### 📈 Screen 5: Trend Analysis (`pages/05_trends.py`)
- **Multi-Metric Comparison**: Overlay up to 3 financial metrics simultaneously (e.g. Sales, Net Profit, Operating Profit, ROE, ROCE, D/E, FCF) over a 10-year historical horizon.
- **YoY Growth Annotations**: Each historical data point displays its absolute figure and year-over-year percentage change (`+X.X%`).

### 🏭 Screen 6: Sector Analysis (`pages/06_sectors.py`)
- **Dynamic Landscape Bubble Chart**: Visualizes constituent positioning with Revenue on the X-axis, ROE on the Y-axis, Market Cap determining bubble radius, and sub-sector determining color.
- **Sector Median Bar Chart**: Side-by-side comparison of sector median ROE, ROCE, NPM, and OPM benchmarks.

### 💰 Screen 7: Capital Allocation Map (`pages/07_capital.py`)
- **Universal Corporate Treemap**: Hierarchical visualization of all 92 companies partitioned into the 8 corporate lifecycle archetypes (*Reinvestor*, *Shareholder Returns*, *Growth Funded by Debt*, etc.).
- **Constituent Drill-Down**: Interactive selector to isolate companies within any lifecycle pattern.

### 📑 Screen 8: Annual Reports Repository (`pages/08_reports.py`)
- **Filing Archive**: Chronological listing of official annual reports dating back 10 years.
- **Direct BSE Links**: One-click download buttons for official regulatory filings.
- **Automated Health Check**: Real-time URL validation with red `Report unavailable` badges for broken links.

---

## 3. Valuation Module & Reports

The platform includes a specialized valuation engine located at [`src/analytics/valuation.py`](file:///c:/blue%20stock/N100%20FINANCIAL%20INTELLIGENCE%20PLATFORM/src/analytics/valuation.py):
- **FCF Yield**: Computed as `(FCF / Market Cap) * 100`.
- **Sector-Relative Multiple Analysis**: Benchmarks each company's P/E multiple against the latest sector median.
- **Overvaluation Flags**:
  - `Caution`: $P/E > 1.5 \times \text{Sector Median}$
  - `Discount`: $P/E < 0.7 \times \text{Sector Median}$
  - `Fair`: Trading within normal valuation band.
- **Generated Artifacts**:
  - `output/valuation_summary.xlsx`: Formatted spreadsheet covering all 92 companies with color-coded valuation flags.
  - `output/valuation_flags.csv`: Filtered subset containing only overvalued (`Caution`) and undervalued (`Discount`) constituents.

To regenerate valuation reports directly via CLI:
```bash
python src/analytics/valuation.py
```

---

## 4. Testing & Verification

The platform maintains a comprehensive test suite covering all four sprints:
```bash
pytest tests/ -v
```

### Test Suite Summary
- **157 Total Tests Passing** (100% pass rate, 0 failures)
  - `tests/dq/`: 14 Data Quality rule tests (DQ-01 to DQ-14)
  - `tests/etl/`: Database connection, normalization, and loader tests (45 tests)
  - `tests/kpi/`: Profitability, leverage, CAGR edge cases, cash flow, and ratio engine tests (51 tests)
  - `tests/screener/`: Screener engine, presets, and export structure tests (13 tests)
  - `tests/peer/`: Percentile ranking, TCS benchmark, inverse D/E, and radar charts tests (11 tests)
  - `tests/dashboard/`: Database caching functions and extreme slider tests (15 tests)
  - `tests/analytics/test_valuation.py`: FCF yield, sector median P/E, and flag generation tests (5 tests)
  - `tests/dashboard/test_performance.py`: Sub-3-second profile load latency benchmarks (3 tests)
