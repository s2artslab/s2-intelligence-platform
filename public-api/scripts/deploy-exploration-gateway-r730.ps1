# Deploy PSLA exploration routes + doc-intel proxy to r730 public-api.
#
# Usage:
#   .\scripts\deploy-exploration-gateway-r730.ps1
#   .\scripts\deploy-exploration-gateway-r730.ps1 -SkipNpmInstall

param(
  [string]$SshHost = "192.168.1.78",
  [string]$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_proxmox",
  [string]$RemoteApiDir = "/opt/s2-ecosystem/public-api",
  [switch]$SkipNpmInstall
)

$ErrorActionPreference = "Stop"
$pub = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "Deploying public-api from $pub to root@${SshHost}:${RemoteApiDir}"

ssh -i $SshKey "root@$SshHost" "mkdir -p ${RemoteApiDir}/lib ${RemoteApiDir}/knowledge ${RemoteApiDir}/scripts"
scp -i $SshKey -r `
  "$pub\lib" `
  "$pub\knowledge" `
  "$pub\server.js" `
  "$pub\package.json" `
  "$pub\package-lock.json" `
  "root@${SshHost}:${RemoteApiDir}/"

if (-not $SkipNpmInstall) {
  ssh -i $SshKey "root@$SshHost" "cd ${RemoteApiDir} && npm ci --omit=dev 2>/dev/null || npm install --omit=dev"
}

# LAN service on r730 (tunnel hostname may not resolve from the host itself)
$docIntelUrl = "http://127.0.0.1:8099"
ssh -i $SshKey "root@$SshHost" @"
set -e
ENV_FILE='${RemoteApiDir}/.env'
touch "`$ENV_FILE"
if grep -q '^DOCUMENT_INTELLIGENCE_URL=' "`$ENV_FILE"; then
  sed -i 's|^DOCUMENT_INTELLIGENCE_URL=.*|DOCUMENT_INTELLIGENCE_URL=${docIntelUrl}|' "`$ENV_FILE"
else
  echo 'DOCUMENT_INTELLIGENCE_URL=${docIntelUrl}' >> "`$ENV_FILE"
fi
if ! grep -q '^S2_KNOWLEDGE_DIR=' "`$ENV_FILE"; then
  echo 'S2_KNOWLEDGE_DIR=./knowledge' >> "`$ENV_FILE"
fi
if grep -q '^BEHIND_NGINX_CORS=' "`$ENV_FILE"; then
  sed -i 's|^BEHIND_NGINX_CORS=.*|BEHIND_NGINX_CORS=true|' "`$ENV_FILE"
else
  echo 'BEHIND_NGINX_CORS=true' >> "`$ENV_FILE"
fi
if grep -q '^CORS_ORIGIN=\*$' "`$ENV_FILE" 2>/dev/null; then
  sed -i 's|^CORS_ORIGIN=\*|CORS_ORIGIN=https://psla.s2artslab.com,https://s2artslab.com|' "`$ENV_FILE"
fi
systemctl daemon-reload 2>/dev/null || true
if systemctl is-enabled s2-public-api.service >/dev/null 2>&1; then
  systemctl restart s2-public-api.service
  systemctl --no-pager status s2-public-api.service | head -n 12
else
  echo 's2-public-api.service not installed — start manually: node server.js'
fi
"@

Write-Host "Smoke: curl -s http://${SshHost}:3010/health (or api.s2artslab.com via tunnel)"
Write-Host "Done."
