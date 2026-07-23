@echo off
REM Ouvre la plateforme de veille CHRUTH dans le navigateur.
cd /d "%~dp0"
python -m streamlit run app_veille.py
pause
