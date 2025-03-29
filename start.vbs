Set WshShell = CreateObject("WScript.Shell")
currentPath = CreateObject("Scripting.FileSystemObject").GetAbsolutePathName(".")
pythonPath = "python.exe"
scriptPath = Chr(34) & currentPath & "\start.py" & Chr(34) ' 确保路径有引号

' 方法1：直接通过cmd调用（推荐）
cmdCommand = "cmd /c " & pythonPath & " " & scriptPath
WshShell.Run "powershell -Command Start-Process -FilePath cmd -ArgumentList '/c " & cmdCommand & "' -Verb runAs", 1, False

Set WshShell = Nothing