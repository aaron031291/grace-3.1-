@echo off
REM Run from anywhere (e.g. double-click or full path). Delegates to start.bat backend.
cd /d "%~dp0"
call "%~dp0start.bat" backend
pause
