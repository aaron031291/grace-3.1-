# Run Postgres/DB connection test from project root.
# Usage: .\test_postgres_connection.ps1
Set-Location $PSScriptRoot\backend
& .\venv_gpu\Scripts\python.exe .\scripts\test_postgres_connection.py
exit $LASTEXITCODE
