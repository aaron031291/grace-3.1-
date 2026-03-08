@echo off
REM Run from anywhere: use full path so it works when you cd to the wrong folder.
set BACKEND=%~dp0
cd /d "%BACKEND%"
if not exist "venv_gpu\Scripts\python.exe" (
    echo ERROR: venv_gpu not found in %BACKEND%
    echo Make sure you are in the Grace project backend folder.
    echo Correct path: C:\Users\aaron\Desktop\grace-3.1--Aaron-new2\backend
    exit /b 1
)
"venv_gpu\Scripts\python.exe" "scripts\test_postgres_connection.py"
exit /b %ERRORLEVEL%
