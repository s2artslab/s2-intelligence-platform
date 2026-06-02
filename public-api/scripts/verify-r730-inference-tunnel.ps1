# Verify local SSH tunnels to r730 gateway + Ollama are reachable.
# Prerequisite: .\scripts\start-r730-inference-tunnel.ps1 running in another terminal.

param(
  [int] $GatewayPort = 3020,
  [int] $OllamaPort = 11434,
  [int] $BitNetPort = 8120,
  [int] $TimeoutSec = 5
)

$ErrorActionPreference = "Stop"

function Test-HttpOk {
  param([string] $Url)
  try {
    $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $TimeoutSec
    return @{ Ok = $true; Status = [int]$resp.StatusCode; Body = $resp.Content.Substring(0, [Math]::Min(120, $resp.Content.Length)) }
  } catch {
    return @{ Ok = $false; Status = 0; Body = $_.Exception.Message }
  }
}

Write-Host ""
Write-Host "  r730 inference tunnel check" -ForegroundColor Cyan
Write-Host ""

$ollama = Test-HttpOk -Url "http://127.0.0.1:${OllamaPort}/api/tags"
$gateway = Test-HttpOk -Url "http://127.0.0.1:${GatewayPort}/health"
$bitnetSidecar = Test-HttpOk -Url "http://127.0.0.1:${BitNetPort}/health"
$bitnetResearch = Test-HttpOk -Url "http://127.0.0.1:${GatewayPort}/api/research/bitnet/status"

$ollamaOk = $ollama.Ok
$gatewayOk = $gateway.Ok
$bitnetSidecarOk = $bitnetSidecar.Ok
$bitnetResearchOk = $bitnetResearch.Ok

Write-Host ("  Ollama  :{0,-4} http://127.0.0.1:{1}/api/tags" -f ($(if ($ollamaOk) { " OK " } else { "FAIL" })), $OllamaPort) -ForegroundColor $(if ($ollamaOk) { "Green" } else { "Red" })
if (-not $ollamaOk) { Write-Host "          $($ollama.Body)" -ForegroundColor DarkGray }

Write-Host ("  Gateway :{0,-4} http://127.0.0.1:{1}/health" -f ($(if ($gatewayOk) { " OK " } else { "FAIL" })), $GatewayPort) -ForegroundColor $(if ($gatewayOk) { "Green" } else { "Red" })
if (-not $gatewayOk) { Write-Host "          $($gateway.Body)" -ForegroundColor DarkGray }

Write-Host ("  BitNet  :{0,-4} http://127.0.0.1:{1}/health (sidecar)" -f ($(if ($bitnetSidecarOk) { " OK " } else { "FAIL" })), $BitNetPort) -ForegroundColor $(if ($bitnetSidecarOk) { "Green" } else { "Yellow" })
Write-Host ("  Research:{0,-4} http://127.0.0.1:{1}/api/research/bitnet/status" -f ($(if ($bitnetResearchOk) { " OK " } else { "FAIL" })), $GatewayPort) -ForegroundColor $(if ($bitnetResearchOk) { "Green" } else { "Yellow" })

Write-Host ""
if (-not ($ollamaOk -and $gatewayOk)) {
  Write-Host "  Start tunnel: .\scripts\start-r730-inference-tunnel.ps1" -ForegroundColor Yellow
  Write-Host "  Runbook: docs\CURSOR_R730_ALIGNMENT.md" -ForegroundColor Yellow
  exit 1
}

Write-Host "  Tunnel healthy." -ForegroundColor Green
if (-not $bitnetSidecarOk) {
  Write-Host "  BitNet sidecar optional — deploy: .\scripts\deploy-bitnet-lane-r730.ps1" -ForegroundColor Yellow
}
exit 0
