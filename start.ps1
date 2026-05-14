# start.ps1
# KafkaPulse - Single startup script
# Run from project root: .\start.ps1

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

$ROOT = $PSScriptRoot

Write-Host ""
Write-Host "Starting KafkaPulse..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Start Docker
Write-Host "[1/5] Starting Kafka + MongoDB (Docker)..." -ForegroundColor Yellow
Set-Location "$ROOT\producer"
docker-compose up -d
Set-Location $ROOT

Write-Host "      Waiting 20s for Kafka to be ready..." -ForegroundColor Gray
Start-Sleep -Seconds 20

# Step 2: Start Producer
Write-Host "[2/5] Starting Producer..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ROOT\producer'; & '$ROOT\.venv\Scripts\Activate.ps1'; python news_producer.py"
Start-Sleep -Seconds 3

# Step 3: Start Consumer
Write-Host "[3/5] Starting Consumer..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ROOT\consumer'; & '$ROOT\.venv\Scripts\Activate.ps1'; python sentiment_consumer.py"
Start-Sleep -Seconds 3

# Step 4: Start FastAPI
Write-Host "[4/5] Starting FastAPI..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ROOT\api'; & '$ROOT\.venv\Scripts\Activate.ps1'; uvicorn main:app --reload --port 8000"
Start-Sleep -Seconds 3

# Step 5: Start React
Write-Host "[5/5] Starting React dashboard..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ROOT\frontend'; npm start"

Write-Host ""
Write-Host "All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard -> http://localhost:3000" -ForegroundColor Cyan
Write-Host "  API       -> http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Kafka     -> localhost:9092"        -ForegroundColor Cyan
Write-Host "  MongoDB   -> localhost:27017"       -ForegroundColor Cyan
Write-Host ""
Write-Host "  Run .\stop.ps1 to stop everything." -ForegroundColor Gray