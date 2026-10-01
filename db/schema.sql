-- ==========================================================
-- N100 Financial Intelligence Platform
-- SQLite Database Schema (nifty100.db)
-- Enforces PRAGMA foreign_keys = ON;
-- ==========================================================

PRAGMA foreign_keys = ON;

-- 1. Master Companies Reference Table
DROP TABLE IF EXISTS companies;
CREATE TABLE companies (
    id TEXT PRIMARY KEY,
    company_logo TEXT,
    company_name TEXT NOT NULL,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value REAL,
    book_value REAL,
    roce_percentage REAL,
    roe_percentage REAL
);

-- 2. Profit & Loss Annual Statements
DROP TABLE IF EXISTS profitandloss;
CREATE TABLE profitandloss (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    opm_percentage REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax_percentage REAL,
    net_profit REAL,
    eps REAL,
    dividend_payout REAL
);

-- 3. Balance Sheet Annual Statements
DROP TABLE IF EXISTS balancesheet;
CREATE TABLE balancesheet (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    other_liabilities REAL,
    total_liabilities REAL,
    fixed_assets REAL,
    cwip REAL,
    investments REAL,
    other_asset REAL,
    total_assets REAL
);

-- 4. Cash Flow Annual Statements
DROP TABLE IF EXISTS cashflow;
CREATE TABLE cashflow (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    operating_activity REAL,
    investing_activity REAL,
    financing_activity REAL,
    net_cash_flow REAL
);

-- 5. Qualitative & Growth Analysis
DROP TABLE IF EXISTS analysis;
CREATE TABLE analysis (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    compounded_sales_growth TEXT,
    compounded_profit_growth TEXT,
    stock_price_cagr TEXT,
    roe TEXT
);

-- 6. Annual Report Documents Repository
DROP TABLE IF EXISTS documents;
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    annual_report TEXT
);

-- 7. Pros & Cons Qualitative Insights
DROP TABLE IF EXISTS prosandcons;
CREATE TABLE prosandcons (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    pros TEXT,
    cons TEXT
);

-- 8. Sector & Industry Classification
DROP TABLE IF EXISTS sectors;
CREATE TABLE sectors (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    broad_sector TEXT,
    sub_sector TEXT,
    index_weight_pct REAL,
    market_cap_category TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 9. Monthly Stock Prices (OHLCV)
DROP TABLE IF EXISTS stock_prices;
CREATE TABLE stock_prices (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    adjusted_close REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 10. Financial Ratios Table
DROP TABLE IF EXISTS financial_ratios;
CREATE TABLE financial_ratios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    net_profit_margin_pct REAL,
    operating_profit_margin_pct REAL,
    return_on_equity_pct REAL,
    debt_to_equity REAL,
    interest_coverage REAL,
    asset_turnover REAL,
    free_cash_flow_cr REAL,
    capex_cr REAL,
    earnings_per_share REAL,
    book_value_per_share REAL,
    dividend_payout_ratio_pct REAL,
    total_debt_cr REAL,
    cash_from_operations_cr REAL,
    roce_pct REAL,
    roa_pct REAL,
    net_debt_cr REAL,
    icr_label TEXT,
    high_leverage_flag INTEGER DEFAULT 0,
    icr_warning_flag INTEGER DEFAULT 0,
    revenue_cagr_3yr REAL,
    revenue_cagr_5yr REAL,
    revenue_cagr_10yr REAL,
    pat_cagr_3yr REAL,
    pat_cagr_5yr REAL,
    eps_cagr_5yr REAL,
    cfo_quality_score REAL,
    capex_intensity_pct REAL,
    fcf_conversion_pct REAL,
    capital_allocation_pattern TEXT,
    composite_quality_score REAL
);

-- 10b. Capital Allocation Table
DROP TABLE IF EXISTS capital_allocation;
CREATE TABLE capital_allocation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    cfo_sign TEXT,
    cfi_sign TEXT,
    cff_sign TEXT,
    pattern_label TEXT,
    cfo_cr REAL,
    cfi_cr REAL,
    cff_cr REAL,
    fcf_cr REAL
);

-- 11. Market Capitalisation & Valuation Multiples
DROP TABLE IF EXISTS market_cap;
CREATE TABLE market_cap (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL,
    year TEXT NOT NULL,
    market_cap_crore REAL,
    enterprise_value_crore REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    dividend_yield_pct REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 12. Peer Groups Mapping
DROP TABLE IF EXISTS peer_groups;
CREATE TABLE peer_groups (
    id INTEGER PRIMARY KEY,
    peer_group_name TEXT NOT NULL,
    company_id TEXT NOT NULL,
    is_benchmark INTEGER DEFAULT 0,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- 13. Peer Percentiles Table
DROP TABLE IF EXISTS peer_percentiles;
CREATE TABLE peer_percentiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    peer_group_name TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    percentile_rank REAL,
    year TEXT NOT NULL
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_pl_comp_year ON profitandloss(company_id, year);
CREATE INDEX IF NOT EXISTS idx_bs_comp_year ON balancesheet(company_id, year);
CREATE INDEX IF NOT EXISTS idx_cf_comp_year ON cashflow(company_id, year);
CREATE INDEX IF NOT EXISTS idx_ratios_comp_year ON financial_ratios(company_id, year);
CREATE INDEX IF NOT EXISTS idx_prices_comp_date ON stock_prices(company_id, date);
CREATE INDEX IF NOT EXISTS idx_sectors_broad ON sectors(broad_sector);
CREATE INDEX IF NOT EXISTS idx_peer_group_name ON peer_groups(peer_group_name);
CREATE INDEX IF NOT EXISTS idx_peer_percentiles_comp ON peer_percentiles(company_id, peer_group_name);
