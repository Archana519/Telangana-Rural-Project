@echo off
setlocal
rem One-command demo of the whole open-data pipeline (offline from cached inputs).
rem Usage: double-click, or  run_demo.bat [--no-open] [--online]
cd /d "%~dp0"
echo.
echo ================================================================================
echo  Telangana rural road planning - full demo
echo ================================================================================
if exist ".venv\Scripts\activate.bat" (
    echo [setup] activating .venv
    call ".venv\Scripts\activate.bat"
) else (
    echo [setup] .venv not found - using the python on PATH
)
set PYTHONIOENCODING=utf-8
python scripts\run_full_demo.py %*
if errorlevel 1 (
    echo.
    echo DEMO FAILED - see demo_output\logs
    exit /b 1
)
endlocal
