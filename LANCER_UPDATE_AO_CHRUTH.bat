@echo off
cd /d "%~dp0"
echo ===============================================
echo CHRUTH - Mise a jour appels d'offres BOAMP
echo ===============================================
python ao_weekly_update.py
echo.
echo Fichier Excel attendu : output\AO_CHRUTH.xlsm
pause
