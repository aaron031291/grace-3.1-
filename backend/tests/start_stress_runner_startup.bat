@echo off
REM Add this to Windows Startup folder to run on boot
REM Location: shell:startup (Win+R, type: shell:startup)

cd /d "%~dp0\..\.."
start /min "" python backend\tests\continuous_stress_runner.py
