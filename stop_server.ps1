# 서버 중지 스크립트
Write-Host "🛑 Stopping FastAPI server..." -ForegroundColor Yellow

# 8000번 포트 사용 중인 프로세스 종료
$processes = netstat -ano | findstr :8000 | ForEach-Object {
    if ($_ -match '\s+(\d+)$') {
        $matches[1]
    }
} | Select-Object -Unique

foreach ($pid in $processes) {
    if ($pid -and $pid -ne "0") {
        Write-Host "Killing process PID: $pid" -ForegroundColor Red
        taskkill /F /PID $pid 2>$null
    }
}

Write-Host "✅ Server stopped." -ForegroundColor Green

