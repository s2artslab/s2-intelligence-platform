# Sync public-api BitNet lane to r730 and run deploy (stub sidecar by default).
#   .\scripts\deploy-bitnet-lane-r730.ps1
#   .\scripts\deploy-bitnet-lane-r730.ps1 -FullModel   # download GGUF (slow)
param(
  [string]$RemoteHost = "root@192.168.1.78",
  [string]$Key = "$env:USERPROFILE\.ssh\id_ed25519_proxmox",
  [switch]$FullModel
)

$ErrorActionPreference = "Stop"
$src = "C:\Users\shast\S2\APPs\s2-intelligence-platform\public-api"
$remote = "/opt/s2-ecosystem/public-api"

Write-Host "Syncing public-api (BitNet lane) to r730..." -ForegroundColor Cyan
& "$src\scripts\sync-public-api-to-r730.ps1" -RemoteHost $RemoteHost -Key $Key

$bitnetScripts = @(
  "bitnet-sidecar-server.py",
  "setup-bitnet-sidecar-r730.sh",
  "deploy-bitnet-lane-r730.sh",
  "bitnet-benchmark-r730.py",
  "bitnet-eval-gate-r730.py",
  "smoke-bitnet-research.js"
)
foreach ($s in $bitnetScripts) {
  scp -i $Key "$src\scripts\$s" "${RemoteHost}:${remote}/scripts/"
}

scp -i $Key "$src\package.json" "${RemoteHost}:${remote}/"

$stubFlag = if ($FullModel) { "0" } else { "1" }
Write-Host "Running deploy on r730 (BITNET_STUB=$stubFlag)..." -ForegroundColor Cyan
ssh -i $Key -o ConnectTimeout=10 $RemoteHost "sed -i 's/\r$//' ${remote}/scripts/*.sh 2>/dev/null; chmod +x ${remote}/scripts/*.sh; BITNET_STUB=$stubFlag bash ${remote}/scripts/deploy-bitnet-lane-r730.sh"
if ($LASTEXITCODE -ne 0) { throw "Remote deploy failed (exit $LASTEXITCODE)" }

Write-Host ""
Write-Host "Deploy complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next on workstation:" -ForegroundColor Yellow
Write-Host "  .\scripts\start-r730-inference-tunnel.ps1"
Write-Host "  Open S2 Research -> BitNet Research -> Sync from gateway"
