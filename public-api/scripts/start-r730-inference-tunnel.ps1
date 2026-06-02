# Start local SSH tunnels to r730 for S2 gateway + Ollama.
# This keeps r730 firewall posture strict (only SSH open) while allowing local tools.
#
# Examples:
#   .\scripts\start-r730-inference-tunnel.ps1
#   .\scripts\start-r730-inference-tunnel.ps1 -OpenLab
#   .\scripts\start-r730-inference-tunnel.ps1 -SshHost 192.168.1.78 -GatewayLocalPort 3020 -OllamaLocalPort 11434

param(
  [string] $SshHost = "192.168.1.78",
  [string] $SshUser = "root",
  [string] $SshKey = "$env:USERPROFILE\.ssh\id_ed25519_proxmox",
  [int] $GatewayLocalPort = 3020,
  [int] $GatewayRemotePort = 3020,
  [int] $OllamaLocalPort = 11434,
  [int] $OllamaRemotePort = 11434,
  [int] $BitNetLocalPort = 8120,
  [int] $BitNetRemotePort = 8120,
  [switch] $OpenLab
)

$ErrorActionPreference = "Stop"

function Test-PortFree {
  param([int] $Port)
  $inUse = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  return -not $inUse
}

if (-not (Test-Path $SshKey)) {
  throw "SSH key not found: $SshKey"
}

if (-not (Test-PortFree -Port $GatewayLocalPort)) {
  throw "Local port $GatewayLocalPort is already in use."
}
if (-not (Test-PortFree -Port $OllamaLocalPort)) {
  throw "Local port $OllamaLocalPort is already in use."
}
if (-not (Test-PortFree -Port $BitNetLocalPort)) {
  throw "Local port $BitNetLocalPort is already in use."
}

$target = "$SshUser@$SshHost"
$bindGateway = "${GatewayLocalPort}:127.0.0.1:${GatewayRemotePort}"
$bindOllama = "${OllamaLocalPort}:127.0.0.1:${OllamaRemotePort}"
$bindBitNet = "${BitNetLocalPort}:127.0.0.1:${BitNetRemotePort}"
$labUrl = "http://127.0.0.1:${GatewayLocalPort}/lab/ake-unified-lora"

Write-Host ""
Write-Host "  r730 inference tunnel active while this window stays open" -ForegroundColor Cyan
Write-Host "  Gateway  : http://127.0.0.1:${GatewayLocalPort} -> ${SshHost}:${GatewayRemotePort}" -ForegroundColor White
Write-Host "  Ollama   : http://127.0.0.1:${OllamaLocalPort} -> ${SshHost}:${OllamaRemotePort}" -ForegroundColor White
Write-Host "  BitNet   : http://127.0.0.1:${BitNetLocalPort} -> ${SshHost}:${BitNetRemotePort}" -ForegroundColor White
Write-Host ""
Write-Host "  Cursor OpenAI Base URL: http://127.0.0.1:${OllamaLocalPort}/v1" -ForegroundColor Yellow
Write-Host "  Gateway health URL     : http://127.0.0.1:${GatewayLocalPort}/health" -ForegroundColor Yellow
Write-Host "  BitNet research API    : http://127.0.0.1:${GatewayLocalPort}/api/research/bitnet/status" -ForegroundColor Yellow
Write-Host "  Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

if ($OpenLab) {
  Start-Process $labUrl | Out-Null
}

ssh -i $SshKey -N -L $bindGateway -L $bindOllama -L $bindBitNet $target
