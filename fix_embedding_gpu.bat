@echo off
REM Fix embedding GPU: use Python 3.12 + PyTorch CUDA so EMBEDDING_DEVICE=cuda works.
REM Run from project root:  .\fix_embedding_gpu.bat
setlocal
cd /d "%~dp0"
set "BACKEND=%~dp0backend"
set "VENV=%BACKEND%\venv"

echo.
echo [FIX] Embedding GPU - Python 3.12 + PyTorch CUDA
echo.

REM Try Python 3.12 first (has PyTorch CUDA wheels)
py -3.12 -c "import sys" 2>nul
if %errorlevel% equ 0 (
    echo [FIX] Recreating venv with Python 3.12...
    if exist "%VENV%" rmdir /s /q "%VENV%" 2>nul
    py -3.12 -m venv "%VENV%"
) else (
    echo [FIX] Python 3.12 not found. Install: winget install Python.Python.3.12
    echo [FIX] Using current Python (GPU may be unavailable)...
    if not exist "%VENV%" python -m venv "%VENV%"
)

call "%VENV%\Scripts\activate.bat"
cd /d "%BACKEND%"
pip install -r requirements.txt -q
python scripts\setup_gpu.py
echo.
echo [FIX] Done. Restart backend:  .\start.bat backend
pause
