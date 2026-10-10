Set WshShell = CreateObject("WScript.Shell")
strCurrentDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strCurrentDir

pythonwPath = strCurrentDir & "\.venv\Scripts\pythonw.exe"
mainPath = strCurrentDir & "\main.py"

If CreateObject("Scripting.FileSystemObject").FileExists(pythonwPath) Then
    WshShell.Run """" & pythonwPath & """ """ & mainPath & """", 0, False
Else
    WshShell.Run "pythonw """ & mainPath & """", 0, False
End If
