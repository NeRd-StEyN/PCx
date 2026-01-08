Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

' Launch the batch file in hidden mode
' We use chr(34) to handle quotes safely for paths with spaces
cmdLine = "cmd.exe /c " & chr(34) & chr(34) & strPath & "\Run_Smart_PC_Shield.bat" & chr(34) & " --minimized" & chr(34)
WshShell.Run cmdLine, 0, False

Set WshShell = Nothing
