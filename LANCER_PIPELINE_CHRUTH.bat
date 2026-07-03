@echo off
cd /d "%~dp0"
echo ================================================================
echo CHRUTH - Pipeline unique
echo ================================================================
echo.
echo Mode par defaut : regeneration locale sans collecte reseau.
echo Pour recollecter, lance en ligne de commande :
echo   python CHRUTH_PIPELINE_UNIQUE.py --collect-ao --collect-prospects
echo.
python CHRUTH_PIPELINE_UNIQUE.py
echo.
pause
