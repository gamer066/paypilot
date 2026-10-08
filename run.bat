@echo off
cd /d "%~dp0"
python seed.py
python -m streamlit run app.py
