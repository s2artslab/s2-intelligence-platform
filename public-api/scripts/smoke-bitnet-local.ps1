#!/usr/bin/env powershell
# Local smoke: BitNet sidecar (stub) + gateway research API without r730.
#   .\scripts\smoke-bitnet-local.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$key = "$env:USERPROFILE\.ssh\id_ed25519_proxmox"

$env:BITNET_STUB = "1"
$env:BITNET_ENABLED = "true"
$env:BITNET_BASE_URL = "http://127.0.0.1:8120"
$env:PORT = "3021"
$env:HOSTED_REQUIRE_BILLING = "false"

function Stop-PortListener {
  param([int]$Port)
  Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

Stop-PortListener -Port 8120
Stop-PortListener -Port 3021
Start-Sleep -Seconds 1

Write-Host "Starting BitNet sidecar (stub) on :8120..." -ForegroundColor Cyan
$sidecar = Start-Process python -ArgumentList "$root\scripts\bitnet-sidecar-server.py" -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 2
$health = Invoke-RestMethod "http://127.0.0.1:8120/health" -TimeoutSec 5
if (-not $health.ok) { throw "Sidecar health failed" }
Write-Host "Sidecar OK stub=$($health.stub_mode)" -ForegroundColor Green

Write-Host "Starting gateway on :3021..." -ForegroundColor Cyan
$gw = Start-Process node -ArgumentList "$root\server.js" -WorkingDirectory $root -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 3

$status = Invoke-RestMethod "http://127.0.0.1:3021/api/research/bitnet/status" -TimeoutSec 10
Write-Host "Research status: bitnet_enabled=$($status.bitnet_enabled) healthy=$($status.bitnet_health.ok)" -ForegroundColor Green

$infer = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:3021/api/research/bitnet/infer" `
  -ContentType "application/json" `
  -Headers @{ "X-S2-Inference-Lane" = "compact" } `
  -Body '{"text":"Tag urgency: high","task_class":"tagging","max_tokens":80}'
Write-Host "Infer lane=$($infer.lane) latency=$($infer.latency_ms)ms" -ForegroundColor Green

Stop-Process -Id $gw.Id -Force -ErrorAction SilentlyContinue
Stop-Process -Id $sidecar.Id -Force -ErrorAction SilentlyContinue
Write-Host "smoke-bitnet-local OK" -ForegroundColor Green
