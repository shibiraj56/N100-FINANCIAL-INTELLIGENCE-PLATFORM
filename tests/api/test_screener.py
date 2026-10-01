"""Unit tests for /api/v1/screener endpoint (Epic 11 / Day 42)."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_screener_min_roe_filter():
    response = client.get("/api/v1/screener?min_roe=15")
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    for comp in results:
        assert comp["return_on_equity_pct"] is not None
        assert comp["return_on_equity_pct"] >= 15.0


def test_screener_invalid_parameter_returns_400():
    # Negative debt to equity
    resp_de = client.get("/api/v1/screener?max_de=-1.5")
    assert resp_de.status_code == 400

    # Negative P/E
    resp_pe = client.get("/api/v1/screener?max_pe=-10")
    assert resp_pe.status_code == 400


def test_screener_multi_criteria_filter():
    response = client.get("/api/v1/screener?min_roe=12&max_de=1.5&min_fcf=0")
    assert response.status_code == 200
    results = response.json()
    assert len(results) > 0
    for comp in results:
        assert comp["return_on_equity_pct"] >= 12.0
        # If non-financial, debt_to_equity <= 1.5
        if str(comp.get("broad_sector", "")).lower() != "financials":
            assert comp["debt_to_equity"] <= 1.5
