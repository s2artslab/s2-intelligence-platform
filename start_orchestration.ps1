# S2 Intelligence - Multi-Agent Orchestration Startup Script
# Starts all services in separate PowerShell windows

Write-Host "="*70 -ForegroundColor Cyan
Write-Host "S2 INTELLIGENCE - MULTI-AGENT ORCHESTRATION" -ForegroundColor Cyan
Write-Host "Starting all services..." -ForegroundColor Cyan
Write-Host "="*70 -ForegroundColor Cyan
Write-Host ""

# Check Python
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.8+" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green

# Check dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
python -c "import fastapi, uvicorn, pydantic, requests, jwt, psutil" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r requirements_orchestration.txt
}
Write-Host "✓ Dependencies ready" -ForegroundColor Green
Write-Host ""

# Start Egregore Service Manager
Write-Host "Starting Egregore Service Manager (Port 9000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python egregore_service_manager.py" -WindowStyle Normal
Start-Sleep -Seconds 2

# Start Intelligence Router
Write-Host "Starting Intelligence Router (Port 3011)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python intelligence_router_production.py" -WindowStyle Normal
Start-Sleep -Seconds 2

# Start API Gateway
Write-Host "Starting API Gateway (Port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python api_gateway.py" -WindowStyle Normal
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "="*70 -ForegroundColor Green
Write-Host "ALL SERVICES STARTED!" -ForegroundColor Green
Write-Host "="*70 -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  • Egregore Manager:    http://localhost:9000" -ForegroundColor White
Write-Host "  • Intelligence Router: http://localhost:3011" -ForegroundColor White
Write-Host "  • API Gateway:         http://localhost:8000" -ForegroundColor White
Write-Host "  • API Documentation:   http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Dashboard:" -ForegroundColor Cyan
Write-Host "  Open orchestration_dashboard.html in browser" -ForegroundColor White
Write-Host ""
Write-Host "Test:" -ForegroundColor Cyan
Write-Host '  curl -X POST http://localhost:8000/v1/query `' -ForegroundColor White
Write-Host '    -H "X-API-Key: sk-demo-key" `' -ForegroundColor White
Write-Host '    -H "Content-Type: application/json" `' -ForegroundColor White
Write-Host '    -d "{\"query\": \"How do I design a scalable system?\"}"' -ForegroundColor White
Write-Host ""
Write-Host "Press any key to stop all services..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Cleanup would go here, but PowerShell windows need manual closing
Write-Host "Close the service windows to stop services." -ForegroundColor Yellow
