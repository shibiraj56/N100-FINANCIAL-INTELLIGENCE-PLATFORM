"""Machine Learning Clustering & Statistical Profiling Engine (Epic 10, Days 36–37).

Implements:
1. 5-Cluster KMeans clustering across 5 normalized core financial metrics.
2. Sector median imputation and StandardScaler normalization.
3. Elbow curve generation (k=2 to 10) -> reports/elbow_plot.png.
4. Cluster labeling and centroid distance calculation -> output/cluster_labels.csv.
5. 10-KPI Pearson correlation heatmap -> reports/correlation_heatmap.png.
6. Sector-relative Z-score outlier detection (|Z| > 3) -> output/outlier_report.csv.
7. Portfolio distribution statistics (P10 to P90, Mean, Std) -> output/portfolio_stats.csv.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.analytics.cagr import calculate_cagr

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(root_dir, "data", "nifty100.db")
if not os.path.exists(DEFAULT_DB_PATH) and os.path.exists(os.path.join(root_dir, "nifty100.db")):
    DEFAULT_DB_PATH = os.path.join(root_dir, "nifty100.db")

REPORTS_DIR = os.path.join(root_dir, "reports")
OUTPUT_DIR = os.path.join(root_dir, "output")

FEATURE_COLS = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]

CORE_10_KPIS = [
    "return_on_equity_pct",
    "roce_pct",
    "debt_to_equity",
    "operating_profit_margin_pct",
    "net_profit_margin_pct",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "free_cash_flow_cr",
    "asset_turnover",
    "pe_ratio",
]


class ClusteringEngine:
    """Executes KMeans clustering, statistical outlier detection, and portfolio distribution analysis."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(REPORTS_DIR, exist_ok=True)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def extract_features(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Extract latest valid annual metrics, sector metadata, and compute 5Y FCF CAGR."""
        conn = sqlite3.connect(self.db_path)
        try:
            df_comps = pd.read_sql("SELECT id, company_name FROM companies ORDER BY id", conn)
            df_sec = pd.read_sql("SELECT company_id, broad_sector FROM sectors", conn)
            df_ratios = pd.read_sql(
                "SELECT * FROM financial_ratios WHERE year != 'TTM' ORDER BY company_id, year",
                conn,
            )
            df_mc = pd.read_sql(
                "SELECT company_id, pe_ratio FROM market_cap WHERE year = '2024-03'",
                conn,
            )
        finally:
            conn.close()

        sec_map = dict(zip(df_sec["company_id"], df_sec["broad_sector"]))
        pe_map = dict(zip(df_mc["company_id"], df_mc["pe_ratio"]))

        cluster_records = []
        kpi_records = []

        for cid in df_comps["id"]:
            sub = df_ratios[df_ratios["company_id"] == cid].sort_values("year")
            valid = sub[sub["operating_profit_margin_pct"].notna() | sub["return_on_equity_pct"].notna()]
            if valid.empty:
                valid = sub

            latest = valid.iloc[-1] if not valid.empty else {}

            # Calculate 5-year FCF CAGR from historical series
            fcf_sub = sub[sub["free_cash_flow_cr"].notna()]
            fcf_cagr = None
            if len(fcf_sub) >= 5:
                start_fcf = fcf_sub.iloc[-5]["free_cash_flow_cr"]
                end_fcf = fcf_sub.iloc[-1]["free_cash_flow_cr"]
                cagr_val, _, _ = calculate_cagr(start_fcf, end_fcf, 5)
                fcf_cagr = cagr_val

            broad_sec = sec_map.get(cid, "Other")

            cluster_records.append({
                "company_id": cid,
                "broad_sector": broad_sec,
                "return_on_equity_pct": latest.get("return_on_equity_pct"),
                "debt_to_equity": latest.get("debt_to_equity"),
                "revenue_cagr_5yr": latest.get("revenue_cagr_5yr"),
                "fcf_cagr_5yr": fcf_cagr,
                "operating_profit_margin_pct": latest.get("operating_profit_margin_pct"),
            })

            # 10 KPIs record for correlation and stats
            kpi_records.append({
                "company_id": cid,
                "broad_sector": broad_sec,
                "return_on_equity_pct": latest.get("return_on_equity_pct"),
                "roce_pct": latest.get("roce_pct"),
                "debt_to_equity": latest.get("debt_to_equity"),
                "operating_profit_margin_pct": latest.get("operating_profit_margin_pct"),
                "net_profit_margin_pct": latest.get("net_profit_margin_pct"),
                "revenue_cagr_5yr": latest.get("revenue_cagr_5yr"),
                "pat_cagr_5yr": latest.get("pat_cagr_5yr"),
                "free_cash_flow_cr": latest.get("free_cash_flow_cr"),
                "asset_turnover": latest.get("asset_turnover"),
                "pe_ratio": pe_map.get(cid),
            })

        df_clustering = pd.DataFrame(cluster_records)
        df_10_kpis = pd.DataFrame(kpi_records)
        return df_clustering, df_10_kpis

    def impute_features(self, df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
        """Impute missing values using sector median, falling back to overall median."""
        df_imputed = df.copy()
        for col in feature_cols:
            sector_medians = df_imputed.groupby("broad_sector")[col].transform("median")
            df_imputed[col] = df_imputed[col].fillna(sector_medians)
            overall_median = df_imputed[col].median()
            if pd.isna(overall_median):
                overall_median = 0.0
            df_imputed[col] = df_imputed[col].fillna(overall_median)
        return df_imputed

    def generate_elbow_plot(self, X_scaled: np.ndarray, output_path: str) -> None:
        """Compute inertia for k from 2 to 10 and plot elbow curve."""
        k_values = list(range(2, 11))
        inertias = []
        for k in k_values:
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            km.fit(X_scaled)
            inertias.append(km.inertia_)

        fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f8fafc")
        ax.plot(k_values, inertias, marker="o", color="#1e3a8a", linewidth=2.0, markersize=6)
        ax.axvline(5, color="#dc2626", linestyle="--", linewidth=1.2, label="Optimal Elbow (k=5)")
        ax.set_title("KMeans Elbow Method for Optimal Clusters (k=2 to 10)", fontsize=11, fontweight="bold", pad=8, color="#0f172a")
        ax.set_xlabel("Number of Clusters (k)", fontsize=9, fontweight="bold")
        ax.set_ylabel("Inertia (Within-Cluster Sum of Squares)", fontsize=9, fontweight="bold")
        ax.set_xticks(k_values)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(fontsize=8.5, loc="upper right")
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close(fig)
        logger.info(f"Elbow plot saved to {output_path}")

    def label_clusters(self, df: pd.DataFrame, kmeans: KMeans, X_scaled: np.ndarray) -> pd.DataFrame:
        """Assign cluster archetypes and compute Euclidean distance from centroid."""
        # Mapping calibrated from cluster centroids/medians
        archetype_names = {
            0: "High-Quality Compounders",
            1: "Defensive Dividend Payers",
            2: "Emerging Growth / Capital Champions",
            3: "Value Cyclicals & Turnarounds",
            4: "Leveraged Financials & Lending Giants",
        }

        labels = kmeans.labels_
        centroids = kmeans.cluster_centers_

        distances = []
        for i, center_idx in enumerate(labels):
            dist = np.linalg.norm(X_scaled[i] - centroids[center_idx])
            distances.append(round(float(dist), 4))

        df_out = pd.DataFrame({
            "company_id": df["company_id"],
            "cluster_id": labels,
            "cluster_name": [archetype_names.get(cid, f"Cluster {cid}") for cid in labels],
            "distance_from_centroid": distances,
        })
        return df_out

    def generate_correlation_heatmap(self, df_kpis: pd.DataFrame, output_path: str) -> None:
        """Generate Pearson correlation heatmap across 10 core financial KPIs."""
        corr_matrix = df_kpis[CORE_10_KPIS].corr(method="pearson")

        fig, ax = plt.subplots(figsize=(8.5, 6.8), dpi=150)
        fig.patch.set_facecolor("#ffffff")

        # Custom clean column display labels
        labels = [
            "ROE %",
            "ROCE %",
            "D/E",
            "OPM %",
            "NPM %",
            "Rev CAGR 5Y",
            "PAT CAGR 5Y",
            "FCF (Cr)",
            "Asset Turn",
            "P/E",
        ]

        sns.heatmap(
            corr_matrix,
            annot=True,
            fmt=".2f",
            cmap="vlag",
            center=0,
            square=True,
            linewidths=0.6,
            cbar_kws={"shrink": 0.8},
            xticklabels=labels,
            yticklabels=labels,
            annot_kws={"size": 7.5},
            ax=ax,
        )
        ax.set_title("Nifty 100 Financial KPIs Pearson Correlation Heatmap", fontsize=11, fontweight="bold", pad=10, color="#0f172a")
        ax.tick_params(axis="both", labelsize=8)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close(fig)
        logger.info(f"Correlation heatmap saved to {output_path}")

    def detect_outliers(self, df_kpis: pd.DataFrame, output_path: str) -> pd.DataFrame:
        """Flag companies where any metric has sector-relative absolute Z-score > 3."""
        outlier_records = []

        for sector, group in df_kpis.groupby("broad_sector"):
            if len(group) < 3:
                # Fall back to overall mean/std if sector too small
                ref_group = df_kpis
            else:
                ref_group = group

            for col in CORE_10_KPIS:
                mean_val = ref_group[col].mean()
                std_val = ref_group[col].std()

                if pd.notna(std_val) and std_val > 0:
                    for _, row in group.iterrows():
                        val = row[col]
                        if pd.notna(val):
                            z = (val - mean_val) / std_val
                            if abs(z) > 3.0:
                                outlier_records.append({
                                    "company_id": row["company_id"],
                                    "broad_sector": sector,
                                    "metric": col,
                                    "value": round(float(val), 2),
                                    "sector_mean": round(float(mean_val), 2),
                                    "sector_std": round(float(std_val), 2),
                                    "z_score": round(float(z), 2),
                                })

        df_outliers = pd.DataFrame(outlier_records)
        df_outliers.to_csv(output_path, index=False)
        logger.info(f"Detected {len(df_outliers)} outlier metrics saved to {output_path}")
        return df_outliers

    def generate_portfolio_stats(self, df_kpis: pd.DataFrame, output_path: str) -> pd.DataFrame:
        """Compute P10, P25, P50, P75, P90, Mean, Std for 10 KPIs across all 92 companies."""
        stats_records = []
        for col in CORE_10_KPIS:
            series = df_kpis[col].dropna()
            stats_records.append({
                "metric": col,
                "P10": round(float(np.percentile(series, 10)), 2) if not series.empty else None,
                "P25": round(float(np.percentile(series, 25)), 2) if not series.empty else None,
                "P50": round(float(np.percentile(series, 50)), 2) if not series.empty else None,
                "P75": round(float(np.percentile(series, 75)), 2) if not series.empty else None,
                "P90": round(float(np.percentile(series, 90)), 2) if not series.empty else None,
                "Mean": round(float(series.mean()), 2) if not series.empty else None,
                "Std": round(float(series.std()), 2) if not series.empty else None,
            })

        df_stats = pd.DataFrame(stats_records)
        df_stats.to_csv(output_path, index=False)
        logger.info(f"Portfolio statistics saved to {output_path}")
        return df_stats

    def run_pipeline(self) -> Dict[str, Any]:
        """Execute entire clustering and statistical profiling pipeline."""
        df_clustering, df_kpis = self.extract_features()

        # Impute features for clustering
        df_imputed = self.impute_features(df_clustering, FEATURE_COLS)

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(df_imputed[FEATURE_COLS])

        # Generate elbow plot
        elbow_path = os.path.join(REPORTS_DIR, "elbow_plot.png")
        self.generate_elbow_plot(X_scaled, elbow_path)

        # Fit KMeans k=5
        kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
        kmeans.fit(X_scaled)

        # Generate cluster labels
        labels_path = os.path.join(OUTPUT_DIR, "cluster_labels.csv")
        df_labels = self.label_clusters(df_clustering, kmeans, X_scaled)
        df_labels.to_csv(labels_path, index=False)
        logger.info(f"Saved {len(df_labels)} cluster assignments to {labels_path}")

        # Correlation heatmap
        heatmap_path = os.path.join(REPORTS_DIR, "correlation_heatmap.png")
        self.generate_correlation_heatmap(df_kpis, heatmap_path)

        # Outliers report
        outliers_path = os.path.join(OUTPUT_DIR, "outlier_report.csv")
        df_outliers = self.detect_outliers(df_kpis, outliers_path)

        # Portfolio stats
        stats_path = os.path.join(OUTPUT_DIR, "portfolio_stats.csv")
        df_stats = self.generate_portfolio_stats(df_kpis, stats_path)

        return {
            "cluster_labels": df_labels,
            "outliers": df_outliers,
            "portfolio_stats": df_stats,
        }


def run_clustering() -> Dict[str, Any]:
    """Convenience runner."""
    engine = ClusteringEngine()
    return engine.run_pipeline()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_clustering()
