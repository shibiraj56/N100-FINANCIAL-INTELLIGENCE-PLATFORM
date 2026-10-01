"""Unit tests for /api/v1/sectors, peers, valuation, and portfolio endpoints (Epic 11 / Day 42)."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_list_all_11_sectors():
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    sectors = response.json()
    assert len(sectors) == 11
    for s in sectors:
        assert "sector" in s
        assert "company_count" in s
        assert s["company_count"] > 0
        assert "median_roe" in s


def test_get_sector_companies_valid_and_404():
    # Valid peer group / sector
    resp_fmcg = client.get("/api/v1/sectors/FMCG/companies")
    assert resp_fmcg.status_code == 200
    comps = resp_fmcg.json()
    assert len(comps) >= 4
    for c in comps:
        assert "ticker" in c
        assert "company_name" in c

    # Support IT abbreviation
    resp_it = client.get("/api/v1/sectors/IT/companies")
    assert resp_it.status_code == 200
    assert len(resp_it.json()) >= 4

    # Unknown sector
    resp_inv = client.get("/api/v1/sectors/UNKNOWN_SECTOR_XYZ/companies")
    assert resp_inv.status_code == 404


def test_get_peer_percentiles_and_radar_compare():
    # Peer group percentiles
    resp_pg = client.get("/api/v1/peers/Automobiles")
    assert resp_pg.status_code == 200
    percentiles = resp_pg.json()
    assert len(percentiles) > 0

    # Unknown peer group
    resp_bad_pg = client.get("/api/v1/peers/UNKNOWN_PEER_GROUP")
    assert resp_bad_pg.status_code == 404

    # Radar compare
    resp_radar = client.get("/api/v1/companies/MARUTI/peers/compare")
    assert resp_radar.status_code == 200
    radar = resp_radar.json()
    assert radar["ticker"] == "MARUTI"
    assert "axes" in radar
    assert len(radar["axes"]) == 8
    assert len(radar["company_values"]) == 8
    assert len(radar["peer_average_values"]) == 8


def test_market_cap_multiples_and_portfolio_stats():
    # Market cap multiples
    resp_mc = client.get("/api/v1/market-cap/TCS")
    assert resp_mc.status_code == 200
    multiples = resp_mc.json()
    assert len(multiples) >= 5
    assert "pe_ratio" in multiples[0]
    assert "market_cap_crore" in multiples[0]

    # Portfolio stats
    resp_stats = client.get("/api/v1/portfolio/stats")
    assert resp_stats.status_code == 200
    stats = resp_stats.json()
    assert len(stats) == 10  # 10 core KPIs
    for s in stats:
        assert "metric" in s
        assert "P50" in s
        assert "Mean" in s


def test_company_documents_endpoint():
    response = client.get("/api/v1/companies/TCS/documents")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) > 0
    for doc in docs:
        assert "annual_report" in doc
        assert "is_url_valid" in doc
        assert isinstance(doc["is_url_valid"], bool)
    assert any(doc["is_url_valid"] is True for doc in docs)
