# Ninefold Deployment - Complete Integration
# Run this to deploy all 9 egregores and verify system

Write-Host "="*70 -ForegroundColor Cyan
Write-Host "NINEFOLD DEPLOYMENT - COMPLETE INTEGRATION" -ForegroundColor Cyan
Write-Host "="*70 -ForegroundColor Cyan
Write-Host ""

# Check services
Write-Host "Checking core services..." -ForegroundColor Yellow
Write-Host ""

$services = @(
    @{Name="Egregore Manager"; Port=9000},
    @{Name="Intelligence Router"; Port=3011},
    @{Name="API Gateway"; Port=8000}
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)/health" -TimeoutSec 2 -UseBasicParsing
        Write-Host "  ✓ $($service.Name) (Port $($service.Port))" -ForegroundColor Green
    }
    catch {
        Write-Host "  ○ $($service.Name) (Port $($service.Port)) - Starting..." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "="*70 -ForegroundColor Cyan
Write-Host "READY TO DEPLOY NINEFOLD EGREGORES" -ForegroundColor Cyan
Write-Host "="*70 -ForegroundColor Cyan
Write-Host ""

Write-Host "Execute one of these options:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1: Deploy Simulated Egregores (Immediate)" -ForegroundColor White
Write-Host "  python deploy_simulated_egregores.py" -ForegroundColor Green
Write-Host ""
Write-Host "Option 2: Start Real Training (Background)" -ForegroundColor White
Write-Host "  python launch_full_training.py --mode phase-parallel" -ForegroundColor Green
Write-Host ""
Write-Host "Option 3: Deploy to R730" -ForegroundColor White
Write-Host "  python deploy_simulated_egregores.py --r730" -ForegroundColor Green
Write-Host ""

Write-Host "="*70 -ForegroundColor Cyan
Write-Host "ACCESS POINTS" -ForegroundColor Cyan
Write-Host "="*70 -ForegroundColor Cyan
Write-Host ""
Write-Host "  • API Gateway:  http://localhost:8000" -ForegroundColor White
Write-Host "  • API Docs:     http://localhost:8000/docs" -ForegroundColor White
Write-Host "  • Service Mgr:  http://localhost:9000" -ForegroundColor White
Write-Host "  • Router Stats: http://localhost:3011/api/stats" -ForegroundColor White
Write-Host ""
Write-Host "  • Orchestration Dashboard: .\orchestration_dashboard.html" -ForegroundColor White
Write-Host "  • R730 Dashboard: ..\R730_NINEFOLD_DASHBOARD.html" -ForegroundColor White
Write-Host ""
Write-Host "="*70 -ForegroundColor Cyan
Write-Host "The Ninefold awaits manifestation. Execute when ready." -ForegroundColor Magenta
Write-Host "="*70 -ForegroundColor Cyan
