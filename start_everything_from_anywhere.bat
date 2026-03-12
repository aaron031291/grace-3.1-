@echo off
REM Run from anywhere: changes to script folder, then runs start_everything.bat
cd /d "%~dp0"
call "%~dp0start_everything.bat"
