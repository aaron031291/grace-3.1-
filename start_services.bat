@echo off
REM Qdrant / external services. Delegates to start.bat services.
cd /d "%~dp0"
call "%~dp0start.bat" services
pause
