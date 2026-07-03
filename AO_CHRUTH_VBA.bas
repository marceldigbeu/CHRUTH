Attribute VB_Name = "AO_CHRUTH"
Option Explicit

Sub Update_AO_CHRUTH()
    Dim projet As String
    Dim region As String
    Dim cmd As String
    projet = ThisWorkbook.Path & "\.."
    region = ""
    On Error Resume Next
    region = Trim(CStr(ThisWorkbook.Sheets("Parametres").Range("B1").Value))
    On Error GoTo 0
    cmd = "cmd.exe /c cd /d """ & projet & """ && python outils\refresh_runner.py ao"
    If Len(region) > 0 Then cmd = cmd & " """ & region & """"
    Shell cmd, vbNormalFocus
    ThisWorkbook.Close SaveChanges:=False
End Sub

Sub Aller_AO_Region()
    On Error Resume Next
    Sheets("AO_Region").Activate
    On Error GoTo 0
End Sub

Sub Aller_AO_Chauds()
    Sheets("AO_CHAUDS").Activate
End Sub

Sub Aller_CRM()
    Sheets("CRM_Suivi").Activate
End Sub

Sub Filtrer_AO_Chauds()
    Sheets("AO_Tous").Activate
    If ActiveSheet.AutoFilterMode Then ActiveSheet.AutoFilterMode = False
    Range("A1").CurrentRegion.AutoFilter Field:=33, Criteria1:="CHAUD"
End Sub

Sub Basculer_Collecte_Donnees()
    ' Active / desactive la collecte reseau CHRUTH.
    ' OFF = les boutons retraitent/exportent les donnees locales sans appeler BOAMP/DCE.
    Dim ws As Worksheet
    Dim etat As String
    Dim nouveau As String
    Dim projet As String
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("Parametres")
    On Error GoTo 0
    If ws Is Nothing Then
        MsgBox "Onglet Parametres introuvable.", vbExclamation
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

Sub Basculer_Notifications()
    ' Active / desactive les alertes email CHRUTH (coupe les emails seulement ;
    ' la collecte et la mise a jour du tableur continuent). L'etat est persiste
    ' cote Python via outils\set_notifications.py pour survivre aux refresh.
    Dim ws As Worksheet
    Dim etat As String
    Dim nouveau As String
    Dim projet As String
    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("Parametres")
    On Error GoTo 0
    If ws Is Nothing Then
        MsgBox "Onglet Parametres introuvable.", vbExclamation
        Exit Sub
    End If
    etat = UCase(Trim(CStr(ws.Range("B2").Value)))
    If etat = "OFF" Then
        nouveau = "ON"
    Else
        nouveau = "OFF"
    End If
    ws.Range("B2").Value = nouveau
    If nouveau = "ON" Then
        ws.Range("B2").Interior.Color = RGB(198, 239, 206)
    Else
        ws.Range("B2").Interior.Color = RGB(255, 199, 206)
    End If
    projet = ThisWorkbook.Path & "\.."
    Shell "cmd.exe /c cd /d """ & projet & """ && python outils\set_notifications.py " & nouveau, vbHide
    ThisWorkbook.Save
    MsgBox "Notifications email : " & nouveau, vbInformation
End Sub

Sub Enregistrer_Destinataires()
    ' Enregistre la liste des destinataires saisie dans l'onglet Parametres
    ' (colonne B a partir de la ligne 5) pour les prochaines alertes email.
    Dim projet As String
    Dim sh As Object
    Dim rc As Long
    ThisWorkbook.Save
    projet = ThisWorkbook.Path & "\.."
    Set sh = CreateObject("WScript.Shell")
    rc = sh.Run("cmd /c cd /d """ & projet & """ && python outils\sync_destinataires.py", 0, True)
    If rc = 0 Then
        MsgBox "Destinataires enregistres. Ils recevront les prochaines alertes.", vbInformation
    Else
        MsgBox "Aucune adresse valide trouvee (colonne B a partir de la ligne 5).", vbExclamation
    End If
End Sub

Sub Generer_Message_AO()
    ' Genere le message IA (email + script) pour l'AO de la ligne selectionnee.
    ' Lit id_ao sur la feuille active, appelle Python (Ollama), affiche le resultat
    ' dans l'onglet Message_IA (a copier/coller).
    Dim idCol As Long, lastCol As Long, c As Long, idAO As String
    Dim projet As String, sh As Object, rc As Long, fichier As String
    Dim ws As Worksheet, stream As Object, contenu As String, lignes() As String, i As Long
    On Error GoTo Erreur

    lastCol = Cells(1, Columns.Count).End(xlToLeft).Column
    For c = 1 To lastCol
        If LCase(Trim(CStr(Cells(1, c).Value))) = "id_ao" Then idCol = c: Exit For
    Next c
    If idCol = 0 Then
        MsgBox "Place-toi sur l'onglet AO_Nettoyage_IDF (colonne id_ao requise).", vbExclamation
        Exit Sub
    End If
    If ActiveCell.Row < 2 Then
        MsgBox "Selectionne d'abord une ligne d'appel d'offres.", vbInformation
        Exit Sub
    End If
    idAO = Trim(CStr(Cells(ActiveCell.Row, idCol).Value))
    If idAO = "" Then
        MsgBox "Pas d'identifiant sur cette ligne.", vbInformation
        Exit Sub
    End If

    projet = ThisWorkbook.Path & "\.."
    Application.StatusBar = "Generation du message IA en cours (Ollama)..."
    Set sh = CreateObject("WScript.Shell")
    rc = sh.Run("cmd /c cd /d """ & projet & """ && python outils\generer_message_ao.py """ & idAO & """", 0, True)
    Application.StatusBar = False

    fichier = projet & "\output\_message_ao.txt"
    If Dir(fichier) = "" Then
        MsgBox "Generation echouee (fichier non produit). Verifie Python/Ollama.", vbExclamation
        Exit Sub
    End If

    Set stream = CreateObject("ADODB.Stream")
    stream.Charset = "utf-8"
    stream.Open
    stream.LoadFromFile fichier
    contenu = stream.ReadText
    stream.Close

    On Error Resume Next
    Set ws = ThisWorkbook.Sheets("Message_IA")
    On Error GoTo Erreur
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Sheets.Add(After:=ThisWorkbook.Sheets(ThisWorkbook.Sheets.Count))
        ws.Name = "Message_IA"
    End If
    ws.Cells.Clear
    ws.Columns(1).NumberFormat = "@"   ' texte : sinon "===..." est pris pour une formule (erreur 1004)
    lignes = Split(Replace(contenu, vbCrLf, vbLf), vbLf)
    For i = 0 To UBound(lignes)
        ws.Cells(i + 1, 1).Value = lignes(i)
    Next i
    ws.Columns(1).ColumnWidth = 110
    ws.Activate
    ws.Range("A1").Select
    MsgBox "Message genere dans l'onglet Message_IA (copier/coller depuis la colonne A).", vbInformation
    Exit Sub
Erreur:
    Application.StatusBar = False
    MsgBox "Erreur generation message : " & Err.Number & " - " & Err.Description, vbExclamation
End Sub

Sub Ouvrir_Lien_AO()
    Dim urlCol As Long
    Dim lastCol As Long
    Dim c As Long
    lastCol = Cells(1, Columns.Count).End(xlToLeft).Column
    For c = 1 To lastCol
        If Cells(1, c).Value = "url_avis" Then
            urlCol = c
            Exit For
        End If
    Next c
    If urlCol = 0 Then
        MsgBox "Colonne url_avis introuvable.", vbExclamation
        Exit Sub
    End If
    If ActiveCell.Row < 2 Then
        MsgBox "Selectionne une ligne AO.", vbInformation
        Exit Sub
    End If
    If Cells(ActiveCell.Row, urlCol).Value <> "" Then
        ThisWorkbook.FollowHyperlink Cells(ActiveCell.Row, urlCol).Value
    Else
        MsgBox "Aucun lien source sur cette ligne.", vbInformation
    End If
End Sub
