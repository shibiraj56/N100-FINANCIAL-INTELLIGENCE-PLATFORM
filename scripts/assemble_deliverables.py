"""Final Deliverables Assembly & Archival Script (Epic 12, Day 44).

Collects all 23 core deliverables into output/final_deliverables/, computes SHA-256 hashes,
validates file size thresholds, writes output/deliverables_manifest.json, and packs
output/nifty100_final_deliverables_day45.zip.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import zipfile
from typing import Any, Dict, List

root_dir = str(Path(__file__).resolve().parent.parent)
OUTPUT_DIR = os.path.join(root_dir, "output")
FINAL_DELIV_DIR = os.path.join(OUTPUT_DIR, "final_deliverables")
ZIP_OUTPUT = os.path.join(OUTPUT_DIR, "nifty100_final_deliverables_day45.zip")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "deliverables_manifest.json")


def compute_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_dir_size(dirpath: str) -> int:
    """Get total size in bytes of all files in directory."""
    total = 0
    for root, _, files in os.walk(dirpath):
        for f in files:
            p = os.path.join(root, f)
            if os.path.isfile(p):
                total += os.path.getsize(p)
    return total


DELIVERABLES_CONFIG = [
    {
        "source": "data/nifty100.db",
        "description": "Master SQLite 3 relational database containing 10 normalized tables with B-tree composite indexes.",
        "sprint": "Sprint 1 - Database Architecture & ETL",
        "is_dir": False,
    },
    {
        "source": "output/dq_audit.csv",
        "description": "Comprehensive audit log of 14 Data Quality rule executions (DQ01 - DQ14).",
        "sprint": "Sprint 1 - Database Architecture & ETL",
        "is_dir": False,
    },
    {
        "source": "output/ratio_edge_cases.log",
        "description": "Log of edge cases handled by Ratio Engine (negative equity, bank carve-outs, CAGR turnaround flags).",
        "sprint": "Sprint 2 - Financial Ratio Engine",
        "is_dir": False,
    },
    {
        "source": "output/screener_output.xlsx",
        "description": "Excel workbook containing full screening outputs for all 6 canonical preset strategies.",
        "sprint": "Sprint 3 - Screener & Peer Comparison Engine",
        "is_dir": False,
    },
    {
        "source": "output/peer_comparison.xlsx",
        "description": "Excel model containing cross-sectional percentile rankings for all 11 peer sectors across 10 metrics.",
        "sprint": "Sprint 3 - Screener & Peer Comparison Engine",
        "is_dir": False,
    },
    {
        "source": "output/valuation_summary.xlsx",
        "description": "Multi-year valuation model with historical multiples (P/E, P/B, EV/EBITDA), FCF yields, and discount tags.",
        "sprint": "Sprint 4 - Dashboard & Valuation Module",
        "is_dir": False,
    },
    {
        "source": "output/valuation_flags.csv",
        "description": "CSV dataset of calculated valuation multiples and overvaluation / discount classification flags.",
        "sprint": "Sprint 4 - Dashboard & Valuation Module",
        "is_dir": False,
    },
    {
        "source": "output/analysis_parsed.csv",
        "description": "Structured tabular dataset of regex-parsed financial growth text from company filings.",
        "sprint": "Sprint 5 - Intelligence, NLP & PDF Reports",
        "is_dir": False,
    },
    {
        "source": "output/pros_cons_generated.csv",
        "description": "Auto-generated fundamental strengths (Pros) and risk factors (Cons) with confidence scores for 92 companies.",
        "sprint": "Sprint 5 - Intelligence, NLP & PDF Reports",
        "is_dir": False,
    },
    {
        "source": "output/cashflow_intelligence.xlsx",
        "description": "Forensic cash flow workbook classifying CFO quality, CapEx intensity, and capital allocation patterns.",
        "sprint": "Sprint 5 - Intelligence, NLP & PDF Reports",
        "is_dir": False,
    },
    {
        "source": "reports/tearsheets",
        "description": "Archive of 92 institutional two-page company tearsheet PDFs with zero overflow errors.",
        "sprint": "Sprint 5 - Intelligence, NLP & PDF Reports",
        "is_dir": True,
    },
    {
        "source": "reports/sector",
        "description": "Archive of 11 comprehensive sector & peer group research PDF reports.",
        "sprint": "Sprint 5 - Intelligence, NLP & PDF Reports",
        "is_dir": True,
    },
    {
        "source": "reports/portfolio",
        "description": "Master 92-company portfolio intelligence compendium PDF report.",
        "sprint": "Sprint 5 - Intelligence, NLP & PDF Reports",
        "is_dir": True,
    },
    {
        "source": "reports/elbow_plot.png",
        "description": "KMeans inertia elbow curve plot confirming k=5 as the optimal cluster count.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
    {
        "source": "reports/correlation_heatmap.png",
        "description": "Pearson correlation matrix heatmap for 10 core financial KPIs across 92 companies.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
    {
        "source": "output/cluster_labels.csv",
        "description": "KMeans clustering assignments for all 92 companies to 5 archetypes with centroid distance metrics.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
    {
        "source": "output/outlier_report.csv",
        "description": "Statistical outlier report identifying metrics with sector-relative absolute Z-scores > 3.0.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
    {
        "source": "output/portfolio_stats.csv",
        "description": "Portfolio distribution statistics (P10, P25, P50, P75, P90, Mean, Std) for 10 financial metrics.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
    {
        "source": "output/perf_notes.md",
        "description": "Benchmark audit report of database query plans, index efficiency, screen load latency, and REST API concurrency.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
    {
        "source": "docs/openapi.json",
        "description": "OpenAPI 3.1 specification schema for all 16 FastAPI REST endpoints under /api/v1.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
    {
        "source": "docs/postman_collection.json",
        "description": "Postman Collection v2.1 export containing all API requests, query parameters, and example tests.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
    {
        "source": "reports/pytest_report.html",
        "description": "Self-contained HTML test execution report showing 214 passing unit & integration tests.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
    {
        "source": "docs/analyst_guide.pdf",
        "description": "Institutional 12-page comprehensive Analyst and Developer Guide with architecture, formulas, and runbook.",
        "sprint": "Sprint 6 - Clustering & REST API",
        "is_dir": False,
    },
]


def assemble():
    os.makedirs(FINAL_DELIV_DIR, exist_ok=True)
    manifest = []

    print(f"Assembling {len(DELIVERABLES_CONFIG)} core deliverables into {FINAL_DELIV_DIR}...")

    for item in DELIVERABLES_CONFIG:
        src = os.path.join(root_dir, item["source"])
        if not os.path.exists(src):
            raise FileNotFoundError(f"Deliverable missing: {src}")

        basename = os.path.basename(src)
        dest = os.path.join(FINAL_DELIV_DIR, basename)

        if item["is_dir"]:
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            size_bytes = get_dir_size(src)
            # Create a combined hash of files in dir
            sha = hashlib.sha256()
            for r, _, fs in sorted(os.walk(src)):
                for f in sorted(fs):
                    p = os.path.join(r, f)
                    with open(p, "rb") as fp:
                        while chunk := fp.read(65536):
                            sha.update(chunk)
            sha_hash = sha.hexdigest()
        else:
            shutil.copy2(src, dest)
            size_bytes = os.path.getsize(src)
            sha_hash = compute_sha256(src)

        manifest.append({
            "deliverable_number": len(manifest) + 1,
            "filename": item["source"],
            "archive_target": basename,
            "file_size_bytes": size_bytes,
            "file_size_human": f"{size_bytes / (1024 * 1024):.2f} MB" if size_bytes > 1024 * 1024 else f"{size_bytes / 1024:.2f} KB",
            "sha256_hash": sha_hash,
            "sprint": item["sprint"],
            "description": item["description"],
        })

    # File size threshold verification
    db_size = os.path.getsize(os.path.join(root_dir, "data", "nifty100.db"))
    tearsheets_size = get_dir_size(os.path.join(root_dir, "reports", "tearsheets"))
    sector_size = get_dir_size(os.path.join(root_dir, "reports", "sector"))

    print(f"Verification: DB Size: {db_size / (1024 * 1024):.2f} MB (Target > 1 MB) -> {'PASS' if db_size > 1024 * 1024 else 'FAIL'}")
    print(f"Verification: Tearsheets Size: {tearsheets_size / (1024 * 1024):.2f} MB (Target > 5 MB) -> {'PASS' if tearsheets_size > 5 * 1024 * 1024 else 'FAIL'}")
    print(f"Verification: Sector Reports Size: {sector_size / (1024 * 1024):.2f} MB (Target > 1 MB) -> {'PASS' if sector_size > 1024 * 1024 else 'FAIL'}")

    assert db_size > 1024 * 1024, "nifty100.db must be > 1 MB"
    assert tearsheets_size > 5 * 1024 * 1024, "Tearsheets directory must be > 5 MB"
    assert sector_size > 1024 * 1024, "Sector reports directory must be > 1 MB"

    # Save deliverables_manifest.json
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Manifest written to {MANIFEST_PATH}")

    # Also copy manifest into final_deliverables
    shutil.copy2(MANIFEST_PATH, os.path.join(FINAL_DELIV_DIR, "deliverables_manifest.json"))

    # Create zip archive containing all final deliverables
    print(f"Creating zip archive at {ZIP_OUTPUT}...")
    with zipfile.ZipFile(ZIP_OUTPUT, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(FINAL_DELIV_DIR):
            for file in files:
                p = os.path.join(root, file)
                arcname = os.path.relpath(p, FINAL_DELIV_DIR)
                zipf.write(p, arcname)

    zip_size = os.path.getsize(ZIP_OUTPUT)
    print(f"Successfully archived all deliverables into {ZIP_OUTPUT} ({zip_size / (1024 * 1024):.2f} MB).")


if __name__ == "__main__":
    assemble()
