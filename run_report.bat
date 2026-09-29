@echo off
chcp 65001 > nul
echo [ISA & 퇴직연금 일일 정산 및 엑셀 리포트 생성 중...]
.\.venv\Scripts\python.exe desktop_main.py
pause
