@echo off
REM GRACE GPU setup: PyTorch + CUDA. Run from project root.
cd /d "%~dp0"

set "BACKEND=%~dp0backend"
set "SCRIPT=%BACKEND%\scripts\setup_gpu.py"

if not exist "%SCRIPT%" (
    echo backend\scripts\setup_gpu.py not found. Run from GRACE project root.
    pause
    exit /b 1
)

echo.
echo === GRACE GPU setup ===
echo.

cd /d "%BACKEND%"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)
if exist "venv_gpu\Scripts\activate.bat" (
    call venv_gpu\Scripts\activate.bat
)

python "%SCRIPT%"

echo.
pause
