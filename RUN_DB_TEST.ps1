# PowerShell: run DB connection test from project root.
# Usage: .\RUN_DB_TEST.ps1   (or right-click → Run with PowerShell)
Set-Location $PSScriptRoot\backend
& .\venv_gpu\Scripts\python.exe .\scripts\test_postgres_connection.py
exit $LASTEXITCODE
