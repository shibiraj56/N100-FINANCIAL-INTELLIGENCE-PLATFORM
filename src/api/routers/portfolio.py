"""Portfolio Distribution Statistics Router (Epic 11, Day 40)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter
import pandas as pd

from src.analytics.clustering import ClusteringEngine

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

root_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
PORTFOLIO_STATS_CSV = os.path.join(root_dir, "output", "portfolio_stats.csv")


@router.get("/stats")
def get_portfolio_statistics() -> List[Dict[str, Any]]:
    """Return P10 through P90 percentile distribution, mean, and standard deviation for 10 core KPIs."""
    if os.path.exists(PORTFOLIO_STATS_CSV):
        df = pd.read_csv(PORTFOLIO_STATS_CSV)
        # Replace NaN with None
        df = df.replace({float("nan"): None})
        return df.to_dict(orient="records")

    # Fallback to computing on the fly
    engine = ClusteringEngine()
    _, df_kpis = engine.extract_features()
    df_stats = engine.generate_portfolio_stats(df_kpis, PORTFOLIO_STATS_CSV)
    df_stats = df_stats.replace({float("nan"): None})
    return df_stats.to_dict(orient="records")
