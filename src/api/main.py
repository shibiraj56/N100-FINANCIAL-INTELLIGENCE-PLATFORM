"""FastAPI Application Main Entry Point (Epic 11, Day 38)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("api")

app = FastAPI(
    title="N100 Financial Intelligence Platform REST API",
    description="Institutional-grade REST API providing real-time financial ratios, screener filters, statement histories, clustering models, and research tearsheets across all 92 Nifty 100 constituents.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Request Logging Middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            f"{request.method} {request.url.path} -> Status {response.status_code} ({process_time_ms} ms)"
        )
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)
        return response


app.add_middleware(RequestLoggingMiddleware)

# 3. Mount all 8 Routers under /api/v1
app.include_router(health.router, prefix="/api/v1")
app.include_router(companies.router, prefix="/api/v1")
app.include_router(screener.router, prefix="/api/v1")
app.include_router(sectors.router, prefix="/api/v1")
app.include_router(peers.router, prefix="/api/v1")
app.include_router(valuation.router, prefix="/api/v1")
app.include_router(portfolio.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.get("/")
def root() -> Dict[str, str]:
    """Root redirect to interactive API documentation."""
    return {
        "platform": "N100 Financial Intelligence Platform",
        "documentation": "/docs",
        "health": "/api/v1/health",
        "version": "1.0.0",
    }


def export_openapi_and_postman(
    output_openapi: str = os.path.join(root_dir, "docs", "openapi.json"),
    output_postman: str = os.path.join(root_dir, "docs", "postman_collection.json"),
) -> None:
    """Export OpenAPI 3.0 specification and generate a Postman collection JSON."""
    os.makedirs(os.path.dirname(output_openapi), exist_ok=True)
    schema = app.openapi()
    with open(output_openapi, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    logger.info(f"Exported OpenAPI 3.0 spec to {output_openapi}")

    # Generate Postman 2.1 collection
    postman_items = []
    for path, methods in schema.get("paths", {}).items():
        for method, details in methods.items():
            postman_items.append({
                "name": details.get("summary", f"{method.upper()} {path}"),
                "request": {
                    "method": method.upper(),
                    "header": [],
                    "url": {
                        "raw": f"http://localhost:8000{path}",
                        "protocol": "http",
                        "host": ["localhost"],
                        "port": "8000",
                        "path": [p for p in path.split("/") if p],
                    },
                    "description": details.get("description", ""),
                },
            })

    postman_collection = {
        "info": {
            "name": "N100 Financial Intelligence API",
            "description": "Postman collection for all 16 endpoints in N100 REST API",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": postman_items,
    }

    with open(output_postman, "w", encoding="utf-8") as f:
        json.dump(postman_collection, f, indent=2)
    logger.info(f"Exported Postman collection to {output_postman}")


if __name__ == "__main__":
    export_openapi_and_postman()
