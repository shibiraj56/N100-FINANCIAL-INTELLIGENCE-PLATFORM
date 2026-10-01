.PHONY: help load ratios test report dashboard api clean

PYTHON = .venv/Scripts/python
PYTEST = .venv/Scripts/pytest
STREAMLIT = .venv/Scripts/streamlit
UVICORN = .venv/Scripts/uvicorn

help:
	@echo "Available targets:"
	@echo "  make load      - Run ETL: load all 12 datasets into SQLite nifty100.db"
	@echo "  make ratios    - Run KPI Ratio Engine: compute ratios & update DB"
	@echo "  make test      - Run full pytest test suite"
	@echo "  make report    - Generate reports"
	@echo "  make dashboard - Launch Streamlit interactive dashboard"
	@echo "  make api       - Start FastAPI REST service"
	@echo "  make clean     - Clean cache and temporary files"

load:
	$(PYTHON) -m src.etl.loader

ratios:
	$(PYTHON) -m src.analytics.ratio_engine

test:
	$(PYTEST) tests/ -v --tb=short --html=reports/pytest_report.html --self-contained-html

report:
	$(PYTHON) -c "from src.reports.tearsheet import run_all; from src.reports.sector_report import run_sector_reports; from src.reports.portfolio_report import run_portfolio_report; run_all(); run_sector_reports(); run_portfolio_report()"

dashboard:
	$(STREAMLIT) run src/dashboard/app.py

api:
	$(UVICORN) src.api.main:app --port 8000 --reload

clean:
	rmdir /s /q __pycache__ 2>nul || true
	rmdir /s /q .pytest_cache 2>nul || true
