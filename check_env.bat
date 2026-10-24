@echo off
chcp 65001 >nul
title J.A.R.V.I.S. - environment check
cd /d "%~dp0"
setlocal enabledelayedexpansion
set "PYEXE="

echo.
echo  Looking for a working Python on this PC...
echo.

for %%C in ("py -3.12" "py -3.13" "py -3" "py" "python" "python3") do (
    if not defined PYEXE (
        for /f "usebackq delims=" %%i in (`%%~C -c "import sys;print(sys.executable)" 2^>nul`) do (
            if not defined PYEXE set "PYEXE=%%i"
        )
    )
)

if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYEXE if exist "C:\Python312\python.exe" set "PYEXE=C:\Python312\python.exe"

if not defined PYEXE goto :nopy

echo  Found: %PYEXE%
echo.
"%PYEXE%" python_env.py

echo.
echo  ============================================================
echo   What do you want to do next?
echo    1 = install / repair the packages
echo    2 = install into a clean .venv   (recommended if pip fails)
echo    3 = run doctor.py   (hardware + API test)
echo    4 = run J.A.R.V.I.S.
echo    5 = exit
echo  ============================================================
set /p c=Type 1-5 and press ENTER: 

if "%c%"=="1" "%PYEXE%" install.py & goto :done
if "%c%"=="2" "%PYEXE%" install.py --venv & goto :done
if "%c%"=="3" "%PYEXE%" doctor.py & goto :done
if "%c%"=="4" "%PYEXE%" jarvis.py & goto :done
goto :done

:nopy
echo  [PROBLEM] No working Python was found by any launcher.
echo.
echo  Most common causes (tick all of these):
echo    a) Python was installed WITHOUT "Add python.exe to PATH"
echo    b) Typing "python" opens the Microsoft Store
echo       ^ fix: Settings ^> Apps ^> Advanced app settings ^> App execution
echo             aliases ^> turn OFF python.exe and python3.exe
echo    c) You are in the wrong folder in the terminal
echo.
echo  Do this:
echo    1. Download Python 3.12 from https://www.python.org/downloads/
echo    2. Run the installer - TICK "Add python.exe to PATH"
echo    3. Close and reopen the terminal
echo    4. Test with:   py -3.12 --version
echo.
echo  Opening the download page now...
start "" https://www.python.org/downloads/release/python-31210/

:done
echo.
pause
