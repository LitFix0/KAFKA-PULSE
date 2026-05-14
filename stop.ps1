# stop.ps1
# KafkaPulse - Stop all services
# Run: .\stop.ps1

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

$ROOT = $PSScriptRoot

Write-Host ""
Write-Host "Stopping KafkaPulse..." -ForegroundColor Cyan
Write-Host ""

# Stop Docker containers
Write-Host "[1/2] Stopping Kafka + MongoDB (Docker)..." -ForegroundColor Yellow
Set-Location "$ROOT\producer"
docker-compose down
Set-Location $ROOT

# Kill all related processes
Write-Host "[2/2] Stopping Python + Node processes..." -ForegroundColor Yellow
Get-Process -Name "python"  -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "node"    -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force

Write-Host ""
Write-Host "All services stopped." -ForegroundColor Green
Write-Host ""