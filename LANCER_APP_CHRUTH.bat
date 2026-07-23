@echo off
REM Ouvre l'application CHRUTH (veille + messages) dans le navigateur.
REM Les deux surfaces sont deux pages d'une meme app : une seule adresse.
cd /d "%~dp0"
echo Demarrage de l'application CHRUTH...
echo (Une fois lancee, ouvre http://localhost:8501 dans ton navigateur)
python -m streamlit run CHRUTH_APP.py
pause
