"""Unit tests for /api/v1/companies endpoints (Epic 11 / Day 42)."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_list_companies_all_92():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200
    companies = response.json()
    assert len(companies) == 92
    assert "id" in companies[0]
    assert "company_name" in companies[0]
    assert "broad_sector" in companies[0]


def test_list_companies_filter_and_search():
    # Filter by sector
    resp_it = client.get("/api/v1/companies?sector=Information Technology")
    assert resp_it.status_code == 200
    it_comps = resp_it.json()
    assert len(it_comps) >= 4
    for c in it_comps:
        assert c["broad_sector"] == "Information Technology"

    # Search by partial ticker or name
    resp_search = client.get("/api/v1/companies?search=TCS")
    assert resp_search.status_code == 200
    search_res = resp_search.json()
    assert any(c["id"] == "TCS" for c in search_res)


def test_get_company_profile_valid_and_404():
    # Valid company
    resp_tcs = client.get("/api/v1/companies/TCS")
    assert resp_tcs.status_code == 200
    data = resp_tcs.json()
    assert data["id"] == "TCS"
    assert "company_name" in data
    assert "latest_ratios" in data
    assert "latest_valuation" in data

    # Unknown company
    resp_inv = client.get("/api/v1/companies/NONEXISTENT_TICKER")
    assert resp_inv.status_code == 404


def test_get_statements_history():
    # P&L
    resp_pl = client.get("/api/v1/companies/TCS/pl?from_year=2020-03")
    assert resp_pl.status_code == 200
    pls = resp_pl.json()
    assert len(pls) >= 4
    for row in pls:
        assert row["company_id"] == "TCS"
        assert row["year"] >= "2020-03"

    # Balance Sheet
    resp_bs = client.get("/api/v1/companies/TCS/bs")
    assert resp_bs.status_code == 200
    assert len(resp_bs.json()) >= 5

    # Cash Flow
    resp_cf = client.get("/api/v1/companies/TCS/cashflow")
    assert resp_cf.status_code == 200
    assert len(resp_cf.json()) >= 5

    # Ratios
    resp_rf = client.get("/api/v1/companies/TCS/ratios?year=2024-03")
    assert resp_rf.status_code == 200
    assert len(resp_rf.json()) == 1


def test_download_tearsheet_pdf():
    response = client.get("/api/v1/companies/TCS/tearsheet")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) >= 30_000
