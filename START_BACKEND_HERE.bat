@echo off
REM Double-click to start backend. Delegates to start.bat backend.
cd /d "%~dp0"
call "%~dp0start.bat" backend
pause
