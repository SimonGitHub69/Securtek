Option Explicit
' Helper locale: apre/sceglie cartelle sul PC Windows anche se Django gira sul Mac server.
Dim sh, fso, here, root, script, pythonCmd, cmd
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

here = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(fso.GetParentFolderName(here))
script = root & "\scripts\securtek_desktop_helper.py"

If Not fso.FileExists(script) Then
  script = here & "\securtek_desktop_helper.py"
End If

If Not fso.FileExists(script) Then
  MsgBox "Helper non trovato. Copia securtek_desktop_helper.py accanto a questo file oppure nel progetto Securtek\scripts\.", vbCritical, "Securtek"
  WScript.Quit 1
End If

pythonCmd = ""
If fso.FileExists(root & "\.venv\Scripts\pythonw.exe") Then
  pythonCmd = """" & root & "\.venv\Scripts\pythonw.exe"""
ElseIf fso.FileExists(root & "\.venv\Scripts\python.exe") Then
  pythonCmd = """" & root & "\.venv\Scripts\python.exe"""
Else
  On Error Resume Next
  pythonCmd = "pythonw"
  On Error GoTo 0
End If

cmd = pythonCmd & " """ & script & """"
sh.Run cmd, 0, False
