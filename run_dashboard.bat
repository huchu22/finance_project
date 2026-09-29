@echo off
chcp 65001 > nul
echo [ISA 퀀트 대시보드 실행 중...]
start "" "http://localhost:8501"
.\.venv\Scripts\streamlit.exe run app.py
pause
