@echo off
REM Bitacora: 2026-08-30 - Bootstrap Windows reproducible de la barrera de calidad.
setlocal

REM Trabajar siempre desde la raiz, aunque el lanzador se invoque desde otra carpeta.
cd /d "%~dp0.."
set "VENV_PY=.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [SETUP] Creating Python 3.14 virtual environment in .venv...
    python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 14) else 1)"
    if errorlevel 1 (
        echo [FAIL] The python command must resolve to Python 3.14.
        exit /b 1
    )
    python -m venv .venv
    if errorlevel 1 (
        echo [FAIL] Python 3.14 could not create .venv.
        exit /b 1
    )
)

REM activate.bat solo afecta a este proceso; no depende de ExecutionPolicy de PowerShell.
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [FAIL] The virtual environment could not be activated.
    exit /b 1
)

echo [SETUP] Installing or verifying development dependencies...
python -m pip install -r requirements-dev.txt
if errorlevel 1 (
    echo [FAIL] Development dependencies could not be installed.
    call deactivate
    exit /b 1
)

python scripts\quality_gate.py
set "GATE_EXIT=%ERRORLEVEL%"
call deactivate

if not "%GATE_EXIT%"=="0" (
    echo [FAIL] Quality gate rejected the current checkout.
    exit /b %GATE_EXIT%
)

echo [PASS] Quality gate accepted the current checkout.
exit /b 0
