@echo off
title Grace 3.1 — Phased Boot
cd /d "%~dp0backend"
set PYTHONIOENCODING=utf-8
if exist .venv\Scripts\activate.bat (call .venv\Scripts\activate.bat) else if exist venv\Scripts\activate.bat (call venv\Scripts\activate.bat)
python grace_boot.py
pause
