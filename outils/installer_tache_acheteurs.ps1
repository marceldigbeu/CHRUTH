# Tâche hebdomadaire : liste des acheteurs actifs de la semaine.
$ErrorActionPreference = "Stop"
$racine = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source
$nom = "CHRUTH Acheteurs - hebdo"

$action = New-ScheduledTaskAction -Execute $python -Argument "-m acheteurs_semaine" -WorkingDirectory $racine
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8:45am
Register-ScheduledTask -TaskName $nom -Action $action -Trigger $trigger -Force | Out-Null
Write-Host "Tache creee : $nom (lundi 08:45)"

# Mise en sommeil de l'ancienne collecte 'toutes entreprises IDF' (non supprimee)
$ancienne = "CHRUTH Prospects - hebdo (carte)"
if (Get-ScheduledTask -TaskName $ancienne -ErrorAction SilentlyContinue) {
    Disable-ScheduledTask -TaskName $ancienne | Out-Null
    Write-Host "Ancienne tache desactivee (non supprimee) : $ancienne"
} else {
    Write-Host "Ancienne tache absente : $ancienne (rien a desactiver)"
}
