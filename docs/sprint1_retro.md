# Sprint 1 Retrospective — Data Foundation (Epic 01: Data Ingestion & ETL)

**Sprint**: Sprint 1 (Days 01–07)  |  **Story Points**: 34 SP  
**Target Delivery Date**: Day 07  |  **Actual Completion**: Day 07  
**Status**: **SIGNED OFF — ALL EXIT CRITERIA MET**

---

## 1. Sprint Goal & Objectives
> **Sprint Goal**: By end of Sprint 1, the team must have a fully loaded and validated SQLite database (`nifty100.db`) containing all 10 tables from 12 source files. All 16 data quality rules must have been run and any CRITICAL failures resolved. The foundation for all subsequent modules must be in place.

---

## 2. Definition of Done & Exit Criteria Verification

| Exit Gate / Metric | Required Benchmark | Achieved Result | Status |
|:---|:---:|:---:|:---:|
| Companies Table Count | `SELECT COUNT(*) FROM companies = 92` | **92** | **PASS** |
| Foreign Key Integrity Check | `PRAGMA foreign_key_check` -> 0 rows | **0 rows** | **PASS** |
| Load Audit Rejections | `load_audit.csv` -> zero CRITICAL rejections | **0 rejections** | **PASS** |
| Unit Test Suite | 35+ ETL unit tests pass | **48 passed / 0 failed** | **PASS** |
| 16 DQ Rules Execution | DQ-01 to DQ-16 run, failure log generated | **1,331 DQ observations logged** | **PASS** |
| 12 Source Datasets | 7 core + 5 supplementary loaded | **12 / 12 datasets loaded** | **PASS** |
| Manual QA Spot-Check | 5 companies verified across time-series | **5 companies verified** | **PASS** |
| Exploratory SQL Queries | 10 analytical queries executed | **10 / 10 queries passed** | **PASS** |

---

## 3. Detailed Data Warehouse Row Counts

| Dataset Name | Table Name | Source Rows (`rows_in`) | Loaded Rows (`rows_loaded`) | Columns | Status |
|:---|:---|:---:|:---:|:---:|:---:|
| `companies.xlsx` | `companies` | 92 | **92** | 12 | SUCCESS |
| `sectors.xlsx` | `sectors` | 92 | **92** | 6 | SUCCESS |
| `profitandloss.xlsx` | `profitandloss` | 1,276 | **1,276** | 15 | SUCCESS |
| `balancesheet.xlsx` | `balancesheet` | 1,312 | **1,312** | 13 | SUCCESS |
| `cashflow.xlsx` | `cashflow` | 1,187 | **1,187** | 7 | SUCCESS |
| `financial_ratios.xlsx` | `financial_ratios` | 1,184 | **1,184** | 16 | SUCCESS |
| `market_cap.xlsx` | `market_cap` | 552 | **552** | 9 | SUCCESS |
| `stock_prices.xlsx` | `stock_prices` | 5,520 | **5,520** | 9 | SUCCESS |
| `documents.xlsx` | `documents` | 1,585 | **1,585** | 4 | SUCCESS |
| `analysis.xlsx` | `analysis` | 20 | **20** | 6 | SUCCESS |
| `prosandcons.xlsx` | `prosandcons` | 16 | **16** | 4 | SUCCESS |
| `peer_groups.xlsx` | `peer_groups` | 56 | **56** | 4 | SUCCESS |

---

## 4. Key Engineering Deliverables
1. **Database Warehouse**:
   - `data/nifty100.db` and root `nifty100.db`
   - Complete 12-table DDL schema with relational indexes in `db/schema.sql` and `sql/schema.sql`
2. **Audit & Validation Logs**:
   - `output/load_audit.csv` & `reports/load_audit.csv`
   - `output/validation_failures.csv` & `reports/validation_failures.csv`
3. **ETL Codebase**:
   - `src/etl/normaliser.py` (and `normalizer.py`): High-resilience `normalize_year()` & `normalize_ticker()`
   - `src/etl/validator.py`: Automated 16 DQ validation rules engine
   - `src/etl/loader.py`: Production-grade DataLoader orchestrator
   - `src/database/connection.py`: PRAGMA foreign keys manager
4. **Testing & QA**:
   - `tests/etl/`: 48 comprehensive unit tests covering normalisers, validator, loader, and database constraints
   - `docs/manual_review_notes.md`: Detailed spot-check review of 5 companies
   - `notebooks/exploratory_queries.sql` & `sql/exploratory_queries.sql`: 10 exploratory audit queries
5. **Project Orchestration**:
   - Root `Makefile` & `make.bat` with targets: `load`, `ratios`, `test`, `report`, `dashboard`, `api`, `clean`
   - Environment templates `.env` and `config/.env.template`

---

## 5. What Went Well & Technical Observations
- **Smart Excel Ingestion**: Automatically handles the 2-row metadata header on the 7 core Excel files (`header=1`) while seamlessly ingesting standard 1-row header files (`header=0`).
- **Flexible Fiscal Year Parsing**: `normalize_year()` correctly unified 40+ distinct year string representations (e.g. `Dec 2012`, `Mar-13`, `Mar 2016 9m`, `2024.5`, `2023`, `FY23`).
- **Zero Foreign Key Violations**: `PRAGMA foreign_key_check` executed cleanly with 0 errors across all relational child tables.
- **Robust Anomaly Tracking**: All minor real-world accounting variances (such as OPM differences, net cash round-offs, or recent IPOs like JIOFIN with <5 years of statements) were cleanly caught and logged to `validation_failures.csv` without aborting the batch pipeline.

---

## 6. Next Steps for Sprint 2 (Financial Ratio Engine, 34 SP)
- Implement profitability metrics: NPM, OPM, ROE, ROCE with bank/NBFC handling.
- Build leverage and coverage ratios: D/E, ICR with debt-free substitutions.
- Compute multi-period CAGR engines (3Y, 5Y, 10Y) with turnaround flag handling.
- Classify capital allocation patterns (8 sign patterns across CFO/CFI/CFF).
