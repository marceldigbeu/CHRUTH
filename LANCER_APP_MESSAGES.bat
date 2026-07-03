@echo off
REM Lance l'app Streamlit de generation de messages CHRUTH (double-clic).
cd /d "%~dp0"
echo Demarrage de l'app Messages CHRUTH...
echo (Une fois lancee, ouvre l'adresse http://localhost:8501 dans ton navigateur)
python -m streamlit run app_messages.py
pause
