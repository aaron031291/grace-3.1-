# GRACE: GPU + Qdrant + Backend + Frontend.
# Run from project folder: .\start_everything.ps1
# Run from anywhere:     & "C:\Users\aaron\Desktop\grace-3.1--Aaron-new2\start_everything.ps1"
Set-Location $PSScriptRoot
$bat = Join-Path $PSScriptRoot "start_everything.bat"
& cmd /c "`"$bat`""
