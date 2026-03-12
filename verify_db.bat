@echo off
REM Quick DB + Genesis Key check (SQLite or PostgreSQL per backend\.env)
REM Run from project root: verify_db.bat
cd /d "%~dp0backend"
python scripts\verify_genesis_sql.py
pause
