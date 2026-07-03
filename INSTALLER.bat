@echo off
REM Installation cle en main du cockpit AO CHRUTH (double-clic).
cd /d "%~dp0"
echo Lancement de l'installation CHRUTH...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0outils\installer.ps1"
