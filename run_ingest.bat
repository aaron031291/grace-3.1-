@echo off
REM Populate Qdrant with documents from knowledge_base. Run from project root.
cd /d "%~dp0"
echo.
echo ===============================================================================
echo    GRACE - Populating vector store (ingestion)
echo ===============================================================================
echo.

cd backend
if exist "venv_gpu\Scripts\python.exe" (
    venv_gpu\Scripts\python.exe reset_and_reingest.py
) else if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe reset_and_reingest.py
) else (
    python reset_and_reingest.py
)
echo.
pause
