# Bootstrap UNIQUE du gabarit AO_CHRUTH_TEMPLATE.xlsm (Excel COM requis).
# Pré-requis : Excel installé + "Accès approuvé au modèle d'objet du projet VBA" activé
#   (Fichier > Options > Centre de gestion de la confidentialité > Paramètres des macros).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$assets = Join-Path $root "assets"
if (-not (Test-Path $assets)) { New-Item -ItemType Directory -Path $assets | Out-Null }
$basPath = Join-Path $root "AO_CHRUTH_VBA.bas"
$target  = Join-Path $assets "AO_CHRUTH_TEMPLATE.xlsm"
if (-not (Test-Path $basPath)) { throw "AO_CHRUTH_VBA.bas introuvable. Lancer d'abord le step 1." }

$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false
$xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Add()
    $ws = $wb.Worksheets.Item(1)
    $ws.Name = "Pilotage"
    # Onglet Parametres (la liste deroulante des regions est ajoutee ensuite via openpyxl,
    # pour gerer proprement les accents). A1 = libelle, B1 = region selectionnee.
    $wsp = $wb.Worksheets.Add([System.Reflection.Missing]::Value, $ws)
    $wsp.Name = "Parametres"
    $wsp.Range("A1").Value = "Region a mettre a jour (AO)"
    $wsp.Range("A2").Value = "Notifications email"
    $wsp.Range("B2").Value = "ON"
    $wsp.Range("B2").Interior.Color = 13561798  # vert (C6EFCE en BGR)
    $wsp.Range("A3").Value = "Collecte donnees"
    $wsp.Range("B3").Value = "OFF"
    $wsp.Range("B3").Interior.Color = 13421823  # rouge clair (FFC7CE en BGR)
    $wsp.Range("A4").Value = "Destinataires des alertes (une adresse par ligne)"
    $wsp.Columns("A").ColumnWidth = 42
    $wsp.Columns("B").ColumnWidth = 32

    $wb.VBProject.VBComponents.Import($basPath) | Out-Null

    # Bouton mise a jour des AO (sur l'onglet Pilotage).
    $btn = $ws.Buttons().Add(420, 10, 150, 28)
    $btn.Caption = "Mettre a jour les AO"
    $btn.OnAction = "Update_AO_CHRUTH"

    # Boutons de l'onglet Parametres (positions en points).
    $btnNotif = $wsp.Buttons().Add(330, 18, 230, 24)
    $btnNotif.Caption = "Activer / Desactiver notifications"
    $btnNotif.OnAction = "Basculer_Notifications"

    $btnCollecte = $wsp.Buttons().Add(330, 50, 230, 24)
    $btnCollecte.Caption = "Activer / Desactiver collecte"
    $btnCollecte.OnAction = "Basculer_Collecte_Donnees"

    $btnDest = $wsp.Buttons().Add(330, 82, 230, 24)
    $btnDest.Caption = "Enregistrer destinataires"
    $btnDest.OnAction = "Enregistrer_Destinataires"

    # Onglet AO_Nettoyage_IDF pre-cree avec un bouton "Generer le message IA".
    # openpyxl remplit cet onglet de donnees a chaque export en conservant le bouton.
    $wsAO = $wb.Worksheets.Add([System.Reflection.Missing]::Value, $wsp)
    $wsAO.Name = "AO_Nettoyage_IDF"
    $btnMsg = $wsAO.Buttons().Add(430, 2, 200, 26)
    $btnMsg.Caption = "Generer le message IA"
    $btnMsg.OnAction = "Generer_Message_AO"

    $wb.SaveAs($target, 52)
    $wb.Close($true)
    Write-Host "Gabarit cree : $target"
}
finally {
    $xl.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
