@echo off
REM Windows 서버 실행 배치
cd /d %~dp0
set PYTHONPATH=%~dp0
set PYTHONUNBUFFERED=1

echo Starting FastAPI server...

REM 가상환경 Python 직접 실행
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

REM reload 필요 시: --reload --reload-dir app 추가

