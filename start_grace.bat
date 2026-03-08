@echo off
REM Start GRACE backend + frontend only (no Qdrant step). Same as: start.bat all
cd /d "%~dp0"
call "%~dp0start.bat" all
