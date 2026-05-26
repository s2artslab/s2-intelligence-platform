# Forward r730 Ake gateway to localhost (bypasses Cloudflare 100s timeout for lab chat).
# Usage: run this script, leave the window open, then open:
#   http://127.0.0.1:3020/lab/ake-unified-lora

$Key = "$env:USERPROFILE\.ssh\id_ed25519_proxmox"
$Host_ = "root@192.168.1.78"

Write-Host "Tunnel: http://127.0.0.1:3020/lab/ake-unified-lora" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray

ssh -i $Key -N -L 3020:127.0.0.1:3020 $Host_
