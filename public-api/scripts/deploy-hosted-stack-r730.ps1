# Deploy public-api env + unified :8100 on r730
param(
  [string]$SshHost = "192.168.1.78",
  [string]$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_proxmox",
  [string]$RemoteApiDir = "/opt/s2-ecosystem/public-api"
)

$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$pub = Join-Path $root "public-api"

ssh -i $SshKey "root@$SshHost" "mkdir -p $RemoteApiDir/scripts $RemoteApiDir/lib $RemoteApiDir/knowledge"
scp -i $SshKey -r "$pub\lib" "$pub\knowledge" "$pub\server.js" "$pub\package.json" "root@${SshHost}:${RemoteApiDir}/"
if (Test-Path "$pub\package-lock.json") {
  scp -i $SshKey "$pub\package-lock.json" "root@${SshHost}:${RemoteApiDir}/"
}
scp -i $SshKey "$pub\scripts\setup-unified-7b-r730.sh" "$pub\scripts\setup-unified-8100-r730.sh" "root@${SshHost}:${RemoteApiDir}/scripts/"
ssh -i $SshKey "root@$SshHost" "chmod +x ${RemoteApiDir}/scripts/setup-unified-7b-r730.sh ${RemoteApiDir}/scripts/setup-unified-8100-r730.sh; bash ${RemoteApiDir}/scripts/setup-unified-7b-r730.sh"

Write-Host "Done. Set UNIFIED_EGREGORE_URL=http://${SshHost}:8100 on gateway."
