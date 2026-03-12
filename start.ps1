# GRACE start script (PowerShell). Usage: .\start.ps1 [ backend | frontend | all | services ]
# In PowerShell you must prefix with .\ when running a script in the current folder.
$bat = Join-Path $PSScriptRoot "start.bat"
$mode = $args[0]
if ($mode) { & cmd /c "`"$bat`" $mode" } else { & cmd /c "`"$bat`"" }
