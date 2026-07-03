$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$aoPath = Join-Path $root "output\AO_CHRUTH.xlsm"
$prospectsPath = Join-Path $root "output\Base_Prospects_CHRUTH.xlsm"
$aoBas = Join-Path $root "AO_CHRUTH_VBA.bas"
$prospectsBas = Join-Path $root "PROSPECTS_VBA.bas"

function Get-ExcelApplication {
    try {
        return [Runtime.InteropServices.Marshal]::GetActiveObject("Excel.Application")
    } catch {
        $script:ExcelWasCreated = $true
        $xl = New-Object -ComObject Excel.Application
        $xl.Visible = $false
        $xl.DisplayAlerts = $false
        return $xl
    }
}

function Get-Workbook($xl, [string]$path) {
    foreach ($wb in $xl.Workbooks) {
        if ($wb.FullName -eq $path) {
            return $wb
        }
    }
    return $xl.Workbooks.Open($path)
}

function Import-ModuleBas($wb, [string]$moduleName, [string]$basPath) {
    try {
        $component = $wb.VBProject.VBComponents.Item($moduleName)
        $wb.VBProject.VBComponents.Remove($component)
    } catch {
        # Module absent : rien a supprimer.
    }
    $wb.VBProject.VBComponents.Import($basPath) | Out-Null
}

function Remove-ButtonByActionOrCaption($ws, [string]$onAction, [string]$caption) {
    $buttons = @()
    foreach ($button in $ws.Buttons()) {
        if ($button.OnAction -eq $onAction -or $button.Caption -eq $caption) {
            $buttons += $button
        }
    }
    foreach ($button in $buttons) {
        $button.Delete()
    }
}

function Move-ButtonByAction($ws, [string]$onAction, [double]$top) {
    foreach ($button in $ws.Buttons()) {
        if ($button.OnAction -eq $onAction) {
            $button.Top = $top
        }
    }
}

$script:ExcelWasCreated = $false
$xl = Get-ExcelApplication
$xl.DisplayAlerts = $false

try {
    if (Test-Path $aoPath) {
        $wb = Get-Workbook $xl $aoPath
        Import-ModuleBas $wb "AO_CHRUTH" $aoBas
        $ws = $wb.Worksheets.Item("Parametres")
        $ws.Range("A3").Value2 = "Collecte donnees"
        $ws.Range("B3").Value2 = "OFF"
        $ws.Range("B3").Interior.Color = 13421823
        Move-ButtonByAction $ws "Enregistrer_Destinataires" 82
        Remove-ButtonByActionOrCaption $ws "Basculer_Collecte_Donnees" "Activer / Desactiver collecte"
        $btn = $ws.Buttons().Add(330, 50, 230, 24)
        $btn.Caption = "Activer / Desactiver collecte"
        $btn.OnAction = "Basculer_Collecte_Donnees"
        $wb.Save()
        Write-Host "AO mis a jour : $aoPath"
    }

    if (Test-Path $prospectsPath) {
        $wb = Get-Workbook $xl $prospectsPath
        Import-ModuleBas $wb "PROSPECTS_CHRUTH" $prospectsBas
        $ws = $wb.Worksheets.Item("MAJ")
        $ws.Range("A3").Value2 = "Collecte donnees"
        $ws.Range("B3").Value2 = "OFF"
        $ws.Range("B3").Interior.Color = 13421823
        Remove-ButtonByActionOrCaption $ws "Basculer_Collecte_Donnees" "Activer / Desactiver collecte"
        $btn = $ws.Buttons().Add(240, 40, 220, 32)
        $btn.Caption = "Activer / Desactiver collecte"
        $btn.OnAction = "Basculer_Collecte_Donnees"
        $wb.Save()
        Write-Host "Prospects mis a jour : $prospectsPath"
    }
} finally {
    if ($script:ExcelWasCreated) {
        $xl.Quit()
    }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
