@echo off
chcp 65001 >nul
title J.A.R.V.I.S. Doctor
cd /d "%~dp0"
setlocal enabledelayedexpansion

set "PYEXE="
if exist ".venv\Scripts\python.exe" set "PYEXE=%CD%\.venv\Scripts\python.exe"
if not defined PYEXE (
    for %%C in ("py -3.12" "py -3" "py" "python" "python3") do (
        if not defined PYEXE (
            for /f "usebackq delims=" %%i in (`%%~C -c "import sys;print(sys.executable)" 2^>nul`) do (
                if not defined PYEXE set "PYEXE=%%i"
            )
        )
    )
)
if not defined PYEXE (
    echo  No Python found. Double-click  check_env.bat  first.
    pause
    exit /b 1
)
"%PYEXE%" doctor.py
pause
