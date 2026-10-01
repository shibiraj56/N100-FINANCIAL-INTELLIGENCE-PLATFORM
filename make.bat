@echo off
set PYTHON=.venv\Scripts\python.exe
set PYTEST=.venv\Scripts\pytest.exe
set STREAMLIT=.venv\Scripts\streamlit.exe
set UVICORN=.venv\Scripts\uvicorn.exe

if "%1"=="load" (
    %PYTHON% -m src.etl.loader
) else if "%1"=="ratios" (
    %PYTHON% -m src.analytics.ratio_engine
) else if "%1"=="test" (
    %PYTEST% tests\ -v --tb=short
) else if "%1"=="report" (
    %PYTHON% -m src.reports.portfolio_summary
) else if "%1"=="dashboard" (
    %STREAMLIT% run src\dashboard\app.py
) else if "%1"=="api" (
    %UVICORN% src.api.main:app --port 8000 --reload
) else if "%1"=="clean" (
    for /d /r . %%d in (__pycache__ .pytest_cache) do @if exist "%%d" rd /s /q "%%d"
) else (
    echo Usage: make.bat [load^|ratios^|test^|report^|dashboard^|api^|clean]
)
