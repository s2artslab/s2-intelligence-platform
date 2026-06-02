# Sync public-api to r730 and kick off dual-lane training (Llama 3.2 QLoRA + BitNet prep).
#
#   .\scripts\run-dual-inference-lanes-r730.ps1              # prepare + start Llama train
#   .\scripts\run-dual-inference-lanes-r730.ps1 -PrepareOnly  # datasets/env only
#   .\scripts\run-dual-inference-lanes-r730.ps1 -BitNet       # also start BitNet LoRA (needs QVAC build)
#   .\scripts\run-dual-inference-lanes-r730.ps1 -Deploy       # after training completes
#
param(
  [string]$RemoteHost = "root@192.168.1.78",
  [string]$Key = "$env:USERPROFILE\.ssh\id_ed25519_proxmox",
  [switch]$PrepareOnly,
  [switch]$BitNet,
  [switch]$Deploy,
  [switch]$PreferLora
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$api = Split-Path -Parent $here

Write-Host ""
Write-Host "  Dual inference lanes - r730 orchestrator" -ForegroundColor Cyan
Write-Host ""

& "$here\sync-public-api-to-r730.ps1" -RemoteHost $RemoteHost -Key $Key

$remoteApi = "/opt/s2-ecosystem/public-api"
$ssh = @("-i", $Key, "-o", "ConnectTimeout=15", "-o", "BatchMode=yes")

if ($Deploy) {
  $prefer = if ($PreferLora) { "true" } else { "false" }
  Write-Host "=== Deploy both lanes (OLLAMA_PREFER_LORA=$prefer) ===" -ForegroundColor Yellow
  ssh @ssh $RemoteHost "OLLAMA_PREFER_LORA=$prefer bash $remoteApi/scripts/setup-dual-inference-lanes-r730.sh deploy"
  Write-Host "Deploy finished." -ForegroundColor Green
  exit 0
}

Write-Host "=== prepare (BitNet env + specialist dataset) ===" -ForegroundColor Yellow
ssh @ssh $RemoteHost "bash $remoteApi/scripts/setup-dual-inference-lanes-r730.sh prepare"

if ($PrepareOnly) {
  Write-Host "Prepare only - next: .\scripts\run-dual-inference-lanes-r730.ps1" -ForegroundColor Green
  exit 0
}

Write-Host "=== Llama 3.2 QLoRA train (background, ~hours on P40) ===" -ForegroundColor Yellow
ssh @ssh $RemoteHost "bash $remoteApi/scripts/setup-dual-inference-lanes-r730.sh llama"

if ($BitNet) {
  Write-Host "=== BitNet LoRA train (requires llama-finetune-lora built) ===" -ForegroundColor Yellow
  ssh @ssh $RemoteHost "bash $remoteApi/scripts/setup-dual-inference-lanes-r730.sh bitnet"
}

Write-Host ""
Write-Host "  Monitor Llama train:" -ForegroundColor Cyan
Write-Host "    ssh -i $Key $RemoteHost 'tail -f /var/log/s2-ake-llama32-qlora-train.log'" -ForegroundColor White
Write-Host "  After train completes:" -ForegroundColor Cyan
Write-Host "    .\scripts\run-dual-inference-lanes-r730.ps1 -Deploy -PreferLora" -ForegroundColor White
Write-Host ""
