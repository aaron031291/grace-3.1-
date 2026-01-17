' Grace Launcher - Hidden Console Version
' Use this if you want the launcher to run without showing a console window
' Point desktop shortcut to this file instead of launch_grace.bat

Set WshShell = CreateObject("WScript.Shell")

' Change to Grace project directory
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Run launcher (0 = hidden window, False = don't wait)
WshShell.Run "python launch_grace.py", 0, False

Set WshShell = Nothing
