@echo off
echo Starting Grace Dev Console on http://localhost:9000
echo.
cd /d "%~dp0"
python -m http.server 9000
