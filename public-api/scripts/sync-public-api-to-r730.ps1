# Sync public-api to r730 (LF line endings for .sh)
param(
  [string]$RemoteHost = "s2-proxmox",
  [string]$Key = "$env:USERPROFILE\.ssh\id_ed25519_proxmox"
)

$src = "C:\Users\shast\S2\APPs\s2-intelligence-platform\public-api"
$remote = "/opt/s2-ecosystem/public-api"

scp -i $Key -r "$src\docs" "${RemoteHost}:${remote}/"
scp -i $Key -r "$src\content" "${RemoteHost}:${remote}/"
scp -i $Key -r "$src\training_data" "${RemoteHost}:${remote}/"
scp -i $Key "$src\server.js" "${RemoteHost}:${remote}/"
scp -i $Key -r "$src\lib" "${RemoteHost}:${remote}/"
scp -i $Key -r "$src\scripts\lib" "${RemoteHost}:${remote}/scripts/"

$scripts = @(
  "setup-unified-production-r730.sh",
  "tier-c-eval-gate-r730.py",
  "tier-d-eval-gate-r730.py",
  "tier-e-eval-gate-r730.py",
  "tier-c-label-mask-collator.py",
  "export-tier-c-dataset-template.py",
  "export-exploration-training-bundle.py",
  "inventory-exploration-corpus.py",
  "build-tier-c-v2-from-blended.py",
  "build-tier-d-long-form-dataset.py",
  "build-tier-e-exploration.py",
  "build-tier-cde-merge.py",
  "train-ake-tier-c-r730.sh",
  "train-ake-tier-cde-r730.sh",
  "train-ake-tier-d-r730.sh",
  "run-ake-field-message-comparison-r730.py",
  "unified-field-message-retry-r730.py",
  "r730-public-api.env"
)
foreach ($s in $scripts) {
  $p = "$src\scripts\$s"
  if (Test-Path $p) {
    scp -i $Key $p "${RemoteHost}:${remote}/scripts/"
  }
}

ssh -i $Key $RemoteHost "sed -i 's/\r$//' ${remote}/scripts/*.sh 2>/dev/null; chmod +x ${remote}/scripts/*.sh 2>/dev/null; cp -f ${remote}/scripts/r730-public-api.env ${remote}/.env 2>/dev/null || true"
Write-Host "Synced to ${RemoteHost}:${remote}"
