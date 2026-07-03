param(
    [ValidateSet("test", "france", "departements")]
    [string]$Scope = "test",

    [string]$Departements = "69",

    [ValidateSet("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
    [string]$Day = "Monday",

    [string]$Time = "09:00",

    [string]$TaskName = "CHRUTH - Mise a jour hebdomadaire"
)

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = (Get-Command python).Source
$Script = Join-Path $Root "weekly_update.py"

if (-not (Test-Path -LiteralPath $Script)) {
    throw "weekly_update.py introuvable : $Script"
}

$Arguments = "`"$Script`" --scope $Scope --label scheduled_$Scope"
if ($Scope -eq "departements") {
    $Arguments += " --departements $Departements"
}

$Action = New-ScheduledTaskAction -Execute $Python -Argument $Arguments -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $Time
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Mise a jour automatique hebdomadaire de la base prospects CHRUTH." `
    -Force | Out-Null

Write-Output "Tache planifiee installee : $TaskName"
Write-Output "Scope : $Scope"
Write-Output "Jour  : $Day"
Write-Output "Heure : $Time"
Write-Output "Script: $Script"
