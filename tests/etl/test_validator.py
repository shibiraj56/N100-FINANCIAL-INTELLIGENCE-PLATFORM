"""
Unit tests for DataValidator and DQ rules.
"""

import pandas as pd
import pytest
from src.etl.validator import DataValidator


def test_validator_dq01_pk_uniqueness():
    companies_df = pd.DataFrame([
        {"id": "TCS", "company_name": "TCS"},
        {"id": "TCS", "company_name": "TCS Duplicate"}
    ])
    validator = DataValidator({"companies": companies_df})
    failures = validator.validate_all()
    dq01_failures = failures[failures["rule_id"] == "DQ-01"]
    assert len(dq01_failures) > 0
    assert dq01_failures.iloc[0]["severity"] == "CRITICAL"


def test_validator_dq02_annual_pk():
    pl_df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "sales": 100},
        {"company_id": "TCS", "year": "2023-03", "sales": 120}
    ])
    validator = DataValidator({"profitandloss": pl_df})
    failures = validator.validate_all()
    dq02_failures = failures[failures["rule_id"] == "DQ-02"]
    assert len(dq02_failures) > 0
    assert dq02_failures.iloc[0]["severity"] == "CRITICAL"


def test_validator_dq03_fk_integrity():
    companies_df = pd.DataFrame([{"id": "TCS", "company_name": "TCS"}])
    pl_df = pd.DataFrame([{"company_id": "UNKNOWN_CORP", "year": "2023-03", "sales": 100}])
    validator = DataValidator({"companies": companies_df, "profitandloss": pl_df})
    failures = validator.validate_all()
    dq03_failures = failures[failures["rule_id"] == "DQ-03"]
    assert len(dq03_failures) == 1
    assert dq03_failures.iloc[0]["severity"] == "CRITICAL"


def test_validator_dq04_bs_balance():
    bs_df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "total_assets": 1000, "total_liabilities": 1050}
    ])
    validator = DataValidator({"balancesheet": bs_df})
    failures = validator.validate_all()
    dq04 = failures[failures["rule_id"] == "DQ-04"]
    assert len(dq04) == 1
    assert dq04.iloc[0]["severity"] == "WARNING"


def test_validator_dq05_opm():
    pl_df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "sales": 100, "operating_profit": 20, "opm_percentage": 25.0}
    ])
    validator = DataValidator({"profitandloss": pl_df})
    failures = validator.validate_all()
    dq05 = failures[failures["rule_id"] == "DQ-05"]
    assert len(dq05) == 1
    assert dq05.iloc[0]["severity"] == "WARNING"


def test_validator_dq06_negative_sales():
    pl_df = pd.DataFrame([
        {"company_id": "TCS", "year": "2023-03", "sales": -50}
    ])
    validator = DataValidator({"profitandloss": pl_df})
    failures = validator.validate_all()
    dq06 = failures[failures["rule_id"] == "DQ-06"]
    assert len(dq06) == 1
    assert dq06.iloc[0]["severity"] == "WARNING"
