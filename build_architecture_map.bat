@echo off
REM Build architecture map from project root. Output: backend\architecture_map.json
cd /d "%~dp0backend"
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python scripts\build_architecture_map.py
pause
