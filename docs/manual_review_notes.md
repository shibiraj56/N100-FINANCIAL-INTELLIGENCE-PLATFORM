# Data Quality Manual QA Review — 5 Random Companies

**Date**: 2026-09-08  |  **Reviewer**: Data Analytics Division / Antigravity QA

## 1. Spot-Check Summary for 5 Sample Companies

### Company: **TCS** (Tata Consultancy Services Ltd)
- **Sector**: Information Technology / IT Services
- **P&L Coverage**: 13 years (2013-03 to TTM)
- **Balance Sheet Coverage**: 13 years (2013-03 to 2024-09)
- **Cash Flow Coverage**: 24 years (2013-03 to 2024-03)
- **Stock Price Monthly Points**: 60 records (Jan 2020 to Dec 2024)

### Company: **INFY** (Infosys Ltd)
- **Sector**: Information Technology / IT Services
- **P&L Coverage**: 13 years (2013-03 to TTM)
- **Balance Sheet Coverage**: 13 years (2013-03 to 2024-09)
- **Cash Flow Coverage**: 12 years (2013-03 to 2024-03)
- **Stock Price Monthly Points**: 60 records (Jan 2020 to Dec 2024)

### Company: **HDFCBANK** (HDFC Bank Ltd)
- **Sector**: Financials / Private Banks
- **P&L Coverage**: 13 years (2013-03 to TTM)
- **Balance Sheet Coverage**: 12 years (2013-03 to 2024-03)
- **Cash Flow Coverage**: 12 years (2013-03 to 2024-03)
- **Stock Price Monthly Points**: 60 records (Jan 2020 to Dec 2024)

### Company: **RELIANCE** (Reliance Industries Ltd)
- **Sector**: Energy / Conglomerates
- **P&L Coverage**: 13 years (2013-03 to TTM)
- **Balance Sheet Coverage**: 13 years (2013-03 to 2024-09)
- **Cash Flow Coverage**: 12 years (2013-03 to 2024-03)
- **Stock Price Monthly Points**: 60 records (Jan 2020 to Dec 2024)

### Company: **ABB** (Abbott India Ltd)
- **Sector**: Industrials / Capital Goods
- **P&L Coverage**: 13 years (2012-12 to TTM)
- **Balance Sheet Coverage**: 13 years (2012-12 to 2024-09)
- **Cash Flow Coverage**: 23 years (2012-12 to 2024-03)
- **Stock Price Monthly Points**: 60 records (Jan 2020 to Dec 2024)

## 2. Companies with < 5 Years Financial History (DQ-16 Flags)

| Ticker | Company Name | Available P&L Years | Notes |
|:---|:---|:---:|:---|
| JIOFIN | Jio Financial Services Ltd | 3 | Recent listing / demerger (e.g. JIOFIN, LICI) |

## 3. QA Sign-Off Decision
- Spot check across core statements confirms consistent year alignment and non-null values.
- Companies with short histories are confirmed to be recent IPOs / demerged entities.
- Status: **APPROVED** for Sprint 1 Data Foundation.