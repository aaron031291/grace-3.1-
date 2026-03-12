# Run GRACE backend only. Delegates to start.bat backend (same as run_backend.bat).
# Uses venv_gpu if present, else venv. In PowerShell: .\run_backend.ps1
$bat = Join-Path $PSScriptRoot "start.bat"
& cmd /c "`"$bat`" backend"
