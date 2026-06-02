# Forward r730 Ake gateway to localhost (bypasses Cloudflare ~100s timeout for lab chat).
# For both gateway + Ollama forwarding, use scripts/start-r730-inference-tunnel.ps1.
# Open the lab URL in Chrome/Edge only - not in Cursor preview.

$Key = Join-Path $env:USERPROFILE ".ssh\id_ed25519_proxmox"
$SshTarget = "root@192.168.1.78"
$LabUrl = "http://127.0.0.1:3020/lab/ake-unified-lora"

Write-Host ""
Write-Host "  Ake lab (unified LoRA) - SSH tunnel" -ForegroundColor Cyan
Write-Host "  $LabUrl" -ForegroundColor White
Write-Host ""
Write-Host "  Opening in your default browser (Chrome/Edge). Not in Cursor." -ForegroundColor Yellow
Write-Host "  Leave this window open. Ctrl+C stops the tunnel." -ForegroundColor Gray
Write-Host ""

$sshArgs = @("-i", $Key, "-N", "-L", "3020:127.0.0.1:3020", $SshTarget)
$proc = Start-Process -FilePath "ssh" -ArgumentList $sshArgs -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 2
if (-not $proc.HasExited) {
  Start-Process $LabUrl
  Write-Host "  If the tab is blank, wait 2s and refresh, or paste the URL above into the address bar." -ForegroundColor Gray
  $proc.WaitForExit()
} else {
  Write-Host "  SSH tunnel failed to start. Run manually:" -ForegroundColor Red
  Write-Host "  ssh -i $Key -N -L 3020:127.0.0.1:3020 $SshTarget" -ForegroundColor Gray
}
