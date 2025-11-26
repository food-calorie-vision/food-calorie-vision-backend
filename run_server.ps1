# Windows 서버 실행 스크립트
$env:PYTHONPATH = $PSScriptRoot
$env:PYTHONUNBUFFERED = "1"

Write-Host "🚀 Starting FastAPI server..." -ForegroundColor Green

# 가상환경 Python 직접 실행 (multiprocessing spawn 문제 회피)
& "$PSScriptRoot\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# reload 필요 시: --reload --reload-dir app 추가

