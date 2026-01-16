@echo off
REM Grace Launcher - Desktop Shortcut Target
REM This file should be used as the target for the desktop shortcut

cd /d "%~dp0"
python launch_grace.py
pause
