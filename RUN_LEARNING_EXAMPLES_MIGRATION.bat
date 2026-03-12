@echo off
REM Run learning_examples column migration (outcome_quality, etc.) for PostgreSQL/SQLite
REM Run this from the Grace project folder, or double-click this file.

set ROOT=%~dp0
set BACKEND=%ROOT%backend
set PY=%BACKEND%\venv_gpu\Scripts\python.exe
set MIGRATION=%BACKEND%\database\migrations\add_learning_example_columns.py

echo ============================================================
echo   Grace - Learning examples migration
echo ============================================================
echo.

if not exist "%PY%" (
    echo [ERROR] Python not found: %PY%
    echo Make sure you are in the Grace project folder.
    pause
    exit /b 1
)

cd /d "%BACKEND%"
"%PY%" "%MIGRATION%"
set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% equ 0 (
    echo [OK] Migration finished.
) else (
    echo [FAIL] Migration exited with code %EXIT_CODE%
)
echo.
pause
exit /b %EXIT_CODE%
