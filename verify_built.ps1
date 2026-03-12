# GRACE deterministic build verification (PowerShell)
# Run from repo root: .\verify_built.ps1
# Or from any folder: & "C:\path\to\grace-3.1--Aaron-new2\verify_built.ps1"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
python scripts\verify_built.py @args
exit $LASTEXITCODE
