Set WshShell = CreateObject("WScript.Shell")
strCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurrentDir

Set fso = CreateObject("Scripting.FileSystemObject")
exePath = strCurrentDir & "\dist\VEXORA\VEXORA.exe"
pythonwPath = strCurrentDir & "\.venv\Scripts\pythonw.exe"
fallbackPythonw = "C:\Users\ASUS\.gemini\antigravity\scratch\VEXORA\.venv\Scripts\pythonw.exe"
mainPath = strCurrentDir & "\main.py"

If fso.FileExists(exePath) Then
    WshShell.Run """" & exePath & """", 1, False
ElseIf fso.FileExists(pythonwPath) Then
    WshShell.Run """" & pythonwPath & """ """ & mainPath & """", 0, False
ElseIf fso.FileExists(fallbackPythonw) Then
    WshShell.Run """" & fallbackPythonw & """ """ & mainPath & """", 0, False
Else
    WshShell.Run "pythonw """ & mainPath & """", 0, False
End If
