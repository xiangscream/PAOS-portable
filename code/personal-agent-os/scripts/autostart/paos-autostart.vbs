' PAOS autostart: launch start.ps1 -NoBrowser with no visible window.
'
' IMPORTANT: keep this file pure ASCII.
' The VBScript engine reads .vbs using the system ANSI code page. On a Chinese
' Windows (GBK) a UTF-8 saved file turns every non-ASCII character into mojibake.
' A hardcoded path containing Chinese characters silently resolved to a
' nonexistent directory, so start.ps1 never ran -- and window mode 0 hid the
' failure completely. Two rules prevent a repeat:
'   1. no non-ASCII characters anywhere in this file
'   2. no hardcoded repo path -- derive it from this script's own location,
'      so Chinese (or any) characters in the path cannot break it
'
' Install / uninstall / rationale: see README.md in this folder (Chinese).

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' This script lives in <repo>\scripts\autostart\ -- go up two levels for the repo root.
autostartDir = fso.GetParentFolderName(WScript.ScriptFullName)
scriptsDir = fso.GetParentFolderName(autostartDir)
repo = fso.GetParentFolderName(scriptsDir)
startScript = fso.BuildPath(fso.BuildPath(repo, "scripts"), "start.ps1")

' Fail loudly. Silent failure under window mode 0 is the hardest kind to debug,
' so a one-off message box is the lesser evil.
If Not fso.FileExists(startScript) Then
    MsgBox "PAOS autostart failed. Not found:" & vbCrLf & startScript, 16, "PAOS"
    WScript.Quit 1
End If

cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & startScript & """ -NoBrowser"
' Arg 2 = 0 hides the window; arg 3 = False means do not wait for exit.
shell.Run cmd, 0, False
