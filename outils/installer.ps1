# Installation "cle en main" du cockpit AO CHRUTH pour un poste Windows.
# Lance par INSTALLER.bat (double-clic). Concu pour des utilisateurs non techniques :
# chaque etape est isolee (try/catch) pour qu'un environnement partiel n'interrompe pas tout.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Etape($titre) { Write-Host ""; Write-Host "=== $titre ===" -ForegroundColor Cyan }
function OK($msg)      { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Avert($msg)   { Write-Host "  [!]  $msg" -ForegroundColor Yellow }

Write-Host "================================================================"
Write-Host " Installation CHRUTH - Cockpit Appels d'Offres (AO)"
Write-Host " Dossier : $root"
Write-Host "================================================================"

# 1) Python -------------------------------------------------------------------
Etape "1/7 Verification de Python"
$python = $null
foreach ($cmd in @("python", "py")) {
    try { $python = (Get-Command $cmd -ErrorAction Stop).Source; break } catch {}
}
if (-not $python) {
    Avert "Python introuvable. Installe-le depuis https://www.python.org/downloads/ (coche 'Add to PATH'), puis relance cet installeur."
    Read-Host "Appuie sur Entree pour quitter"
    exit 1
}
OK "Python : $python"

# 2) Dependances --------------------------------------------------------------
Etape "2/7 Installation des dependances Python"
try {
    & $python -m pip install --quiet --upgrade pip
    & $python -m pip install --quiet -r (Join-Path $root "requirements.txt")
    OK "Dependances installees (requests, pandas, openpyxl)."
} catch {
    Avert "Echec pip : $($_.Exception.Message)"
}

# 3) Excel : dossier de confiance (macros actives sans avertissement) ---------
Etape "3/7 Autorisation des macros Excel (dossier de confiance)"
try {
    $verKey = Get-ChildItem "HKCU:\Software\Microsoft\Office" -ErrorAction Stop |
        Where-Object { $_.PSChildName -match '^\d+\.\d+$' } |
        Sort-Object { [double]$_.PSChildName } -Descending |
        Select-Object -First 1
    $ver = $verKey.PSChildName
    $tlBase = "HKCU:\Software\Microsoft\Office\$ver\Excel\Security\Trusted Locations"
    $slot = Join-Path $tlBase "CHRUTH"
    New-Item -Path $slot -Force | Out-Null
    New-ItemProperty -Path $slot -Name "Path" -Value ($root + "\") -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $slot -Name "AllowSubFolders" -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $slot -Name "Description" -Value "CHRUTH cockpit AO" -PropertyType String -Force | Out-Null
    OK "Dossier de confiance ajoute (Office $ver)."
} catch {
    Avert "Impossible de configurer le dossier de confiance : $($_.Exception.Message)"
    Avert "Les macros pourront demander une autorisation manuelle a l'ouverture."
}

# 4) Template : (re)construction si absent ------------------------------------
Etape "4/7 Modele Excel avec boutons"
$template = Join-Path $root "assets\AO_CHRUTH_TEMPLATE.xlsm"
if (Test-Path $template) {
    OK "Modele deja present : $template"
} else {
    try {
        & (Join-Path $root "outils\creer_template_xlsm.ps1")
        OK "Modele genere."
    } catch {
        Avert "Modele non genere (Excel requis) : $($_.Exception.Message)"
    }
}

# 5) Identifiants email d'alerte ---------------------------------------------
Etape "5/7 Configuration de l'email d'alerte (Gmail)"
$secrets = Join-Path $root "alertes_secrets.json"
$dejaConfig = $false
if (Test-Path $secrets) {
    try {
        $j = Get-Content $secrets -Raw | ConvertFrom-Json
        if ($j.smtp_password -and $j.smtp_password -notmatch 'REMPLACER|placeholder|xxxx') { $dejaConfig = $true }
    } catch {}
}
if ($dejaConfig) {
    OK "Email d'alerte deja configure (alertes_secrets.json)."
} else {
    Write-Host "  Pour envoyer les alertes, il faut un compte Gmail + un 'mot de passe d'application'."
    Write-Host "  (Compte Google > Securite > Validation en 2 etapes > Mots de passe des applications)"
    $rep = Read-Host "  Configurer maintenant ? (O/N)"
    if ($rep -match '^[OoYy]') {
        $user = Read-Host "  Adresse Gmail expediteur"
        $secure = Read-Host "  Mot de passe d'application (16 caracteres)" -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        $pwd = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        $obj = [ordered]@{ smtp_user = $user; smtp_password = $pwd }
        ($obj | ConvertTo-Json) | Set-Content -Path $secrets -Encoding UTF8
        OK "Identifiants enregistres (alertes_secrets.json, non partage)."
    } else {
        Avert "A configurer plus tard dans alertes_secrets.json avant que les alertes ne partent."
    }
}

# 6) Taches planifiees (collecte + alerte automatiques) ----------------------
Etape "6/7 Automatisation (taches planifiees Windows)"
try {
    $set = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    $aAlerte = New-ScheduledTaskAction -Execute $python -Argument "ao_alertes_run.py" -WorkingDirectory $root
    $tAlerte = New-ScheduledTaskTrigger -Once -At ([datetime]::Today.AddHours(7)) `
        -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
    Register-ScheduledTask -TaskName "CHRUTH AO - Alerte horaire" -Action $aAlerte -Trigger $tAlerte `
        -Settings $set -Description "Collecte + alerte email des nouveaux AO nettoyage IDF." -Force | Out-Null

    $aHebdo = New-ScheduledTaskAction -Execute $python -Argument "ao_weekly_update.py" -WorkingDirectory $root
    $tHebdo = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "07:00"
    Register-ScheduledTask -TaskName "CHRUTH AO - Mise a jour hebdomadaire" -Action $aHebdo -Trigger $tHebdo `
        -Settings $set -Description "Regeneration hebdomadaire du tableur AO." -Force | Out-Null

    OK "Taches creees : alerte horaire + mise a jour hebdomadaire (lundi 7h)."
} catch {
    Avert "Taches planifiees non creees : $($_.Exception.Message)"
}

# 7) Premiere generation + raccourci bureau ----------------------------------
Etape "7/7 Premiere mise a jour + raccourci bureau"
try {
    Write-Host "  Generation du cockpit (peut prendre 1-2 min, collecte BOAMP)..."
    & $python (Join-Path $root "ao_weekly_update.py") | Out-Null
    OK "Cockpit genere : output\AO_CHRUTH.xlsm"
} catch {
    Avert "Generation initiale non terminee : $($_.Exception.Message)"
}
try {
    $cockpit = Join-Path $root "output\AO_CHRUTH.xlsm"
    $desktop = [Environment]::GetFolderPath("Desktop")
    $sh = New-Object -ComObject WScript.Shell
    $lnk = $sh.CreateShortcut((Join-Path $desktop "Cockpit AO CHRUTH.lnk"))
    $lnk.TargetPath = $cockpit
    $lnk.WorkingDirectory = (Join-Path $root "output")
    $lnk.Description = "Cockpit Appels d'Offres CHRUTH"
    $lnk.Save()
    OK "Raccourci 'Cockpit AO CHRUTH' cree sur le Bureau."
} catch {
    Avert "Raccourci non cree : $($_.Exception.Message)"
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host " Installation terminee." -ForegroundColor Green
Write-Host " Ouvre 'Cockpit AO CHRUTH' sur le Bureau pour demarrer." -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Read-Host "Appuie sur Entree pour fermer"
