@echo off
REM =============================================================================
REM GRACE deterministic build verification (Windows CMD or PowerShell)
REM =============================================================================
REM From repo root: verify_built.bat   or in PowerShell: .\verify_built.ps1
REM Runs scripts/verify_built.py; writes verification_manifest.json.
REM Exit code 0 only if all required checks pass.
REM =============================================================================

setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"
python scripts\verify_built.py %*
set EXIT=%errorlevel%
endlocal
exit /b %EXIT%
