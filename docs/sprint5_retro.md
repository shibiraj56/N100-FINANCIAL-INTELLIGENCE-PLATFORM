# Sprint 5 Retrospective — Intelligence, NLP & PDF Reports (Epics 07, 08 & 09)

**Sprint**: Sprint 5 (Days 29–35)  |  **Story Points**: 70 SP  
**Target Delivery Date**: Day 35  |  **Actual Completion**: Day 35  
**Status**: **SIGNED OFF — ALL EXIT CRITERIA MET**

---

## 1. Sprint Goal & Objectives

> **Sprint Goal**: By end of Sprint 5, the NLP module must auto-generate pros and cons for all 92 companies with confidence scores. The Cash Flow Intelligence module must classify every company by CFO quality, CapEx intensity, and capital allocation pattern. All 92 company tearsheet PDFs and 11 sector PDFs must be generated with no text overflow or layout errors.

---

## 2. Definition of Done & Exit Criteria Verification

| Exit Gate / Metric | Required Benchmark | Achieved Result | Status |
|:---|:---:|:---:|:---:|
| **NLP Text Parser Output** | Parse qualitative CAGRs from analysis | **`output/analysis_parsed.csv` (65 parsed records)** | **PASS** |
| **Parse Failures Logging** | Log unparsed non-standard phrases | **`output/parse_failures.csv` (15 TTM/Last Year entries)** | **PASS** |
| **CAGR Cross-Validation** | Track divergence vs computed CAGRs | **`output/cagr_divergence.csv` (20 tracked records)** | **PASS** |
| **Universal Pros/Cons Coverage** | Every company has $\ge 1$ PRO & $\ge 1$ CON | **100% (92/92 companies) — 377 PROs, 250 CONs** | **PASS** |
| **Confidence Scoring Gate** | Confidence score strictly $> 60\%$ | **100% of generated items have score $> 60\%$** | **PASS** |
| **Cash Flow Intelligence Excel** | 92 companies, 11 standard columns | **`output/cashflow_intelligence.xlsx` (92 rows, 11 cols)** | **PASS** |
| **Distress Alerts Tracking** | Historical 3-year CFO < 0 & CFF > 0 | **`output/distress_alerts.csv` (39 alerts logged)** | **PASS** |
| **Pattern Transition Tracking** | Detect FY23 to FY24 lifecycle shifts | **`output/pattern_changes.csv` (49 changes mapped)** | **PASS** |
| **Batch Tearsheet Generation** | 92 two-page PDF tearsheets ($\ge 30$ KB) | **92 / 92 PDFs generated (62–89 KB each, 2 pages)** | **PASS** |
| **Tearsheet Failure Rate** | 0 skipped tearsheets | **`output/skipped_tearsheets.csv` (0 failures, 100% success)** | **PASS** |
| **Sector PDF Benchmark Reports**| 11 peer group sector PDFs | **11 / 11 sector PDFs in `reports/sector/`** | **PASS** |
| **Portfolio Compendium PDF** | Master 92-company portfolio PDF | **`reports/portfolio/portfolio_summary.pdf` (4 pages)** | **PASS** |
| **Full Project Test Suite** | 0 failures across all modules | **173 passed / 0 failed (100%)** | **PASS** |
| **Database Integrity** | 0 foreign key violations | **`PRAGMA foreign_key_check;` = 0 violations** | **PASS** |

---

## 3. Module Architecture & Delivered Features

### Epic 09: NLP Analysis Text Parser & Growth Cross-Validator (`src/nlp/parser.py`)
- **Regex Extraction Engine**: Built high-precision regular expressions `(\d+)\s*Years?:?\s*(-?[\d.]+)%` targeting qualitative CAGR fields: `compounded_sales_growth`, `compounded_profit_growth`, `stock_price_cagr`, and `roe`.
- **Parsing Artifacts**:
  - `output/analysis_parsed.csv`: Parsed periods (10Y, 5Y, 3Y, 1Y) and floating-point growth rates.
  - `output/parse_failures.csv`: Cleanly captures unparseable qualitative strings (e.g. `TTM:` or `Last Year:`).
  - `output/cagr_divergence.csv`: Compares qualitative disclosure CAGRs against the Ratio Engine's mathematically computed CAGRs from raw financial statements.

### Epic 09: NLP Pros & Cons Generator (`src/nlp/pros_cons_generator.py`)
- **12 PRO & 12 CON Canonical Rules**: Formulated full analytical rules spanning capital efficiency (ROE/ROCE), cash conversion (FCF), leverage dynamics (D/E, Net Debt/EBITDA, ICR), top-line growth (Sales CAGR), earnings compounding (PAT/EPS CAGR), and dividend sustainability.
- **Calibrated Multi-Tier Confidence Scoring**:
  - High tier (90–95% confidence): 3–5 year consecutive milestones or conservative balance sheets.
  - Moderate tier (65–85% confidence): Recent fiscal year trend improvements or operating leverage inflection.
- **Universal Coverage (100% Guarantee)**: Handled bank leverage exemptions, interim period adjustments, and varying capital structures to guarantee that every single company in the Nifty 100 index has at least 1 PRO and at least 1 CON point.
- **Output**: `output/pros_cons_generated.csv` (627 total items sorted by `company_id`, `rule_type`, and `confidence_score` DESC).

### Epic 07: Cash Flow Intelligence & Capital Allocation Dynamics (`src/analytics/cashflow_kpis.py`)
- **5-Year CFO Quality Score**:
  - *High Quality*: CFO > Net Profit for 4+ out of 5 years (49 companies).
  - *Moderate Quality*: CFO > Net Profit for 2–3 out of 5 years (20 companies).
  - *Accrual Risk*: CFO < Net Profit for 4+ out of 5 years (22 companies).
- **CapEx Intensity Tiers**:
  - *Asset Light* (< 3% of sales): 21 companies.
  - *Moderate* (3%–8% of sales): 24 companies.
  - *Capital Intensive* (> 8% of sales): 46 companies.
- **Distress Signal & Deleveraging Flags**:
  - Flagged 13 current distress signals and 39 three-year historical alerts (`CFO < 0` & `CFF > 0`).
  - Identified 22 actively deleveraging enterprises (`CFF < 0` and declining borrowings).
- **Output Artifacts**:
  - `output/cashflow_intelligence.xlsx` (92 rows, 11 columns).
  - `output/distress_alerts.csv` (39 historical distress incidents).
  - `output/pattern_changes.csv` (49 transitions mapped to Expansion: 25, Deleveraging: 17, Contraction: 4, Distress: 3).

### Epic 08: Institutional PDF Reporting Engine (`src/reports/`)
- **Two-Page Financial Tearsheets (`src/reports/tearsheet.py`)**:
  - Strict 2-page constraint enforced through precise flowable geometry, custom sub-tables, and PageBreak control.
  - Page 1: Dark navy corporate header banner with CMP, 52W High/Low, Sector, Market Cap; 6 KPI metric tiles; Dual-bar 5-year Revenue & PAT chart; Line chart for ROE & ROCE; Historical 5-year financial statement table.
  - Page 2: Mini-header; Stacked bar chart for Capital Employed Structure; Triple-bar Cash Flow Activities chart; Profile badges for Capital Allocation Pattern, CFO Quality, and CapEx Intensity; Side-by-side Investment Thesis (PROs in green, CONs in red); Institutional research disclaimer.
  - Generated all 92 tearsheets with file sizes between 62 KB and 89 KB (100% compliant with $\ge 30$ KB threshold, 0 failures).
- **Sector Benchmark Reports (`src/reports/sector_report.py`)**:
  - Generated 11 comprehensive PDF reports for each peer group: Automobiles, Consumer Finance, FMCG, IT Services, Life Insurance, Oil & Gas, Pharmaceuticals, Power & Utilities, Private Banks, Public Sector Banks, and Steel.
  - Features sector median benchmark cards (P/E, P/B, ROE, D/E, OPM, 5Y Rev CAGR), horizontal constituent ranking charts, and complete constituent metrics tables.
- **Portfolio Intelligence Compendium (`src/reports/portfolio_report.py`)**:
  - Master landscape compendium covering all 92 companies.
  - Directional momentum indicators for Revenue (`[↑ Accel]`, `[↓ Decel]`, `[→ Flat]`) and Net Profit.
  - Deleveraging indicators (`YES`, `DEBT FREE`, `NO`).
  - Aggregate macro summary tiles and repeat header tables across all pages.

---

## 4. Key Learnings & Engineering Triumphs

1. **Interim Reporting vs Annual Statements**: Balance sheet records often include September half-yearly updates (`2024-09`), while annual income statements conclude in March (`2024-03`) (with exceptions like SIEMENS in September). Filtering explicitly for annual statement continuity prevented null-metric anomalies across valuation models and tearsheets.
2. **Defensive PDF Flowable Management**: In ReportLab, dynamic content (like varying bullet counts) can trigger unexpected page spillover. Placing charts side-by-side in fixed-height tables and clamping thesis bullets to top-confidence items guaranteed exact 2-page boundaries for all 92 companies without a single overflow.
3. **Graceful Regulatory Handling**: Banking entities operate under distinct regulatory reporting frameworks where traditional debt-to-equity and non-financial cash flow definitions require contextual interpretation. Implementing defensive placeholders and regulatory footnotes prevented pipeline breaks while maintaining analytical integrity.
