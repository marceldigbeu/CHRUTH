@echo off
cd /d "%~dp0"
title CHRUTH - Demarrage no-code
echo ================================================================
echo CHRUTH - Demarrage no-code
echo ================================================================
echo.
echo Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo Python est introuvable.
  echo Installe Python depuis https://www.python.org/downloads/
  echo Coche "Add python.exe to PATH", puis relance ce fichier.
  pause
  exit /b 1
)
echo.
echo Installation / verification des dependances...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo Certaines dependances n'ont pas pu etre installees.
  echo Verifie la connexion internet puis relance ce fichier.
  pause
  exit /b 1
)
echo.
echo Ouverture de l'interface CHRUTH...
start "" pythonw CHRUTH_NO_CODE.py
exit /b 0
