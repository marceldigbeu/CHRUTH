$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$assets = Join-Path $root "assets"
if (-not (Test-Path $assets)) { New-Item -ItemType Directory -Path $assets | Out-Null }
$bas = Join-Path $root "PROSPECTS_VBA.bas"
$target = Join-Path $assets "PROSPECTS_TEMPLATE.xlsm"
if (-not (Test-Path $bas)) { throw "PROSPECTS_VBA.bas introuvable." }
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false
try {
    $wb = $xl.Workbooks.Add()
    $ws = $wb.Worksheets.Item(1)
    $ws.Name = "MAJ"
    $ws.Range("A1").Value2 = "CHRUTH - Prospects : cliquer le bouton pour mettre a jour"
    $ws.Range("A3").Value2 = "Collecte donnees"
    $ws.Range("B3").Value2 = "OFF"
    $ws.Range("B3").Interior.Color = 13421823  # rouge clair (FFC7CE en BGR)
    $wb.VBProject.VBComponents.Import($bas) | Out-Null
    $btn = $ws.Buttons().Add(20, 40, 200, 32)
    $btn.Caption = "Mettre a jour les prospects"
    $btn.OnAction = "Update_Prospects"
    $btnCollecte = $ws.Buttons().Add(240, 40, 220, 32)
    $btnCollecte.Caption = "Activer / Desactiver collecte"
    $btnCollecte.OnAction = "Basculer_Collecte_Donnees"
    $wb.SaveAs($target, 52)
    $wb.Close($true)
    Write-Host "Gabarit prospects cree : $target"
} finally { $xl.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null }
