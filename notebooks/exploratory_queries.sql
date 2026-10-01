-- ============================================================================
-- N100 Financial Intelligence Platform
-- Exploratory SQL Queries (10 Queries)
-- Sprint 1: Data Foundation Verification
-- ============================================================================

-- Query 1: Table Row Counts Summary
-- Verifies populated tables and ensures zero empty tables
SELECT 'companies' AS table_name, COUNT(*) AS total_rows FROM companies
UNION ALL
SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL
SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL
SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL
SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL
SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL
SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL
SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL
SELECT 'documents', COUNT(*) FROM documents
UNION ALL
SELECT 'peer_groups', COUNT(*) FROM peer_groups;

-- Query 2: Missing / Null Values Check on Key Analytical Columns
SELECT 
    COUNT(*) AS total_pl_records,
    SUM(CASE WHEN sales IS NULL THEN 1 ELSE 0 END) AS null_sales,
    SUM(CASE WHEN operating_profit IS NULL THEN 1 ELSE 0 END) AS null_op,
    SUM(CASE WHEN net_profit IS NULL THEN 1 ELSE 0 END) AS null_pat,
    SUM(CASE WHEN eps IS NULL THEN 1 ELSE 0 END) AS null_eps
FROM profitandloss;

-- Query 3: Financial History Year Coverage per Company
SELECT 
    company_id,
    COUNT(year) AS recorded_years,
    MIN(year) AS earliest_year,
    MAX(year) AS latest_year
FROM profitandloss
GROUP BY company_id
ORDER BY recorded_years DESC, company_id ASC;

-- Query 4: Companies with < 5 Years of History (DQ-16 Flag)
SELECT 
    c.id,
    c.company_name,
    COUNT(p.year) AS available_years
FROM companies c
LEFT JOIN profitandloss p ON c.id = p.company_id
GROUP BY c.id, c.company_name
HAVING available_years < 5
ORDER BY available_years ASC;

-- Query 5: Balance Sheet Equality Audit (Assets vs Liabilities)
SELECT 
    company_id,
    year,
    total_assets,
    total_liabilities,
    ROUND(total_assets - total_liabilities, 2) AS diff,
    ROUND(ABS(total_assets - total_liabilities) / total_assets * 100, 2) AS diff_pct
FROM balancesheet
WHERE ABS(total_assets - total_liabilities) / total_assets >= 0.01
ORDER BY diff_pct DESC;

-- Query 6: Top 10 Companies by Latest Fiscal Year Sales
SELECT 
    p.company_id,
    c.company_name,
    p.year,
    p.sales AS revenue_cr,
    p.operating_profit AS ebitda_cr,
    p.net_profit AS pat_cr
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
WHERE p.year = '2024-03'
ORDER BY p.sales DESC
LIMIT 10;

-- Query 7: Sector Breakdown and Aggregate Index Weight
SELECT 
    broad_sector,
    COUNT(DISTINCT company_id) AS company_count,
    ROUND(SUM(index_weight_pct), 2) AS total_index_weight
FROM sectors
GROUP BY broad_sector
ORDER BY total_index_weight DESC;

-- Query 8: Cash Flow Realization Ratio (CFO vs Net Profit)
SELECT 
    p.company_id,
    p.year,
    p.net_profit AS pat_cr,
    c.operating_activity AS cfo_cr,
    ROUND(c.operating_activity / NULLIF(p.net_profit, 0), 2) AS cfo_to_pat_ratio
FROM profitandloss p
JOIN cashflow c ON p.company_id = c.company_id AND p.year = c.year
WHERE p.net_profit > 1000 AND p.year = '2024-03'
ORDER BY cfo_to_pat_ratio DESC
LIMIT 15;

-- Query 9: Valuation Overview by Sector (Median P/E and P/B Multiples for 2024)
SELECT 
    s.broad_sector,
    COUNT(DISTINCT m.company_id) AS companies_covered,
    ROUND(AVG(m.pe_ratio), 2) AS avg_pe,
    ROUND(AVG(m.pb_ratio), 2) AS avg_pb,
    ROUND(AVG(m.dividend_yield_pct), 2) AS avg_div_yield
FROM market_cap m
JOIN sectors s ON m.company_id = s.company_id
WHERE m.year = '2024-03' OR m.year = '2024'
GROUP BY s.broad_sector
ORDER BY avg_pe DESC;

-- Query 10: Annual Report Repository Coverage Count
SELECT 
    c.id,
    c.company_name,
    COUNT(d.year) AS report_count,
    MIN(d.year) AS earliest_report,
    MAX(d.year) AS latest_report
FROM companies c
LEFT JOIN documents d ON c.id = d.company_id
GROUP BY c.id, c.company_name
ORDER BY report_count DESC;
