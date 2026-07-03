Attribute VB_Name = "PROSPECTS_CHRUTH"
Option Explicit

Sub Basculer_Collecte_Donnees()
    ' Active / desactive la collecte reseau CHRUTH.
    ' OFF = les boutons retraitent/exportent les donnees locales sans appeler l'API.
    Dim ws As Worksheet
    Dim etat As String
    Dim nouveau As String
    Dim projet As String
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("MAJ")
    On Error GoTo 0
    If ws Is Nothing Then
        MsgBox "Onglet MAJ introuvable.", vbExclamation
        Exit Sub
    End If
    etat = UCase(Trim(CStr(ws.Range("B3").Value)))
    If etat = "OFF" Then
        nouveau = "ON"
    Else
        nouveau = "OFF"
    End If
    ws.Range("B3").Value = nouveau
    If nouveau = "ON" Then
        ws.Range("B3").Interior.Color = RGB(198, 239, 206)
    Else
        ws.Range("B3").Interior.Color = RGB(255, 199, 206)
    End If
    projet = ThisWorkbook.Path & "\.."
    Shell "cmd.exe /c cd /d """ & projet & """ && python outils\set_collecte.py " & nouveau, vbHide
    ThisWorkbook.Save
    MsgBox "Collecte de donnees : " & nouveau, vbInformation
End Sub

Sub Update_Prospects()
    Dim rep As VbMsgBoxResult
    Dim projet As String, mode As String
    projet = ThisWorkbook.Path & "\.."
    rep = MsgBox("Mise a jour des prospects." & vbCrLf & _
                 "Oui = Rafraichir vite (rapide)" & vbCrLf & _
                 "Non = Tout recollecter la France (LONG)", _
                 vbYesNoCancel + vbQuestion, "CHRUTH - Prospects")
    If rep = vbCancel Then Exit Sub
    If rep = vbYes Then mode = "vite" Else mode = "complet"
    Shell "cmd.exe /c cd /d """ & projet & """ && python outils\refresh_runner.py prospects " & mode, vbNormalFocus
    ThisWorkbook.Close SaveChanges:=False
End Sub
