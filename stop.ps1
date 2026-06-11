# stop.ps1
# KafkaPulse - Stop all services
# Run: .\stop.ps1

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

$ROOT = $PSScriptRoot

Write-Host ""
Write-Host "Stopping KafkaPulse..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Close the named PowerShell windows
Write-Host "[1/3] Closing service windows..." -ForegroundColor Yellow

$titles = @(
    "KafkaPulse-Producer",
    "KafkaPulse-Consumer",
    "KafkaPulse-Embedding",
    "KafkaPulse-API",
    "KafkaPulse-Frontend"
)

Get-Process powershell -ErrorAction SilentlyContinue | ForEach-Object {
    if ($titles -contains $_.MainWindowTitle) {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

# Step 2: Kill any leftover processes (safety net)
Write-Host "[2/3] Stopping leftover Python + Node processes..." -ForegroundColor Yellow
Get-Process -Name "python"  -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "node"    -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force

# Step 3: Stop Docker containers
Write-Host "[3/3] Stopping Kafka + MongoDB (Docker)..." -ForegroundColor Yellow
Set-Location "$ROOT\producer"
docker-compose down
Set-Location $ROOT

Write-Host ""
Write-Host "All services stopped." -ForegroundColor Green
Write-Host ""