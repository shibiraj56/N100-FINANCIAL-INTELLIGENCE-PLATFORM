"""Unit tests for GET /api/v1/health endpoint (Epic 11 / Day 42)."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health_endpoint_status_and_schema():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], (int, float))

    db_counts = data.get("db_row_counts", {})
    expected_tables = [
        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "analysis",
        "documents",
        "prosandcons",
        "sectors",
        "stock_prices",
        "market_cap",
    ]
    for table in expected_tables:
        assert table in db_counts, f"Table '{table}' missing from health check response"
        assert db_counts[table] > 0, f"Table '{table}' has 0 rows"

    assert db_counts["companies"] == 92
    assert db_counts["profitandloss"] == 1276
    assert db_counts["balancesheet"] == 1312
    assert db_counts["cashflow"] == 1187
    assert db_counts["stock_prices"] == 5520
