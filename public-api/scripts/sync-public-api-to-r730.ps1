# Sync public-api to r730 (LF line endings for .sh)
param(
  [string]$RemoteHost = "root@192.168.1.78",
  [string]$Key = "$env:USERPROFILE\.ssh\id_ed25519_proxmox"
)

$ErrorActionPreference = "Stop"
$src = "C:\Users\shast\S2\APPs\s2-intelligence-platform\public-api"
$remote = "/opt/s2-ecosystem/public-api"

ssh -i $Key -o ConnectTimeout=10 -o BatchMode=yes $RemoteHost "echo ok" | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Cannot reach r730 via SSH ($RemoteHost). Connect to LAN/VPN and retry."
}

scp -i $Key -r "$src\docs" "${RemoteHost}:${remote}/"
if ($LASTEXITCODE -ne 0) { throw "scp failed (docs)" }
scp -i $Key -r "$src\content" "${RemoteHost}:${remote}/"
scp -i $Key -r "$src\training_data" "${RemoteHost}:${remote}/"
scp -i $Key "$src\server.js" "${RemoteHost}:${remote}/"
scp -i $Key "$src\package.json" "${RemoteHost}:${remote}/"
scp -i $Key -r "$src\lib" "${RemoteHost}:${remote}/"
scp -i $Key -r "$src\scripts\lib" "${RemoteHost}:${remote}/scripts/"

$scripts = @(
  "setup-unified-production-r730.sh",
  "setup-bitnet-sidecar-r730.sh",
  "deploy-bitnet-lane-r730.sh",
  "bitnet-sidecar-server.py",
  "bitnet-benchmark-r730.py",
  "bitnet-eval-gate-r730.py",
  "smoke-bitnet-research.js",
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
  "build-tier-c-ollama-distill.py",
  "audit-ake-assistant-quality.py",
  "train-ake-tier-c-r730.sh",
  "train-ake-tier-cde-r730.sh",
  "train-ake-tier-d-r730.sh",
  "train-ake-llama32-qlora-r730.sh",
  "train_egregore_on_llama32.py",
  "deploy-ake-lora-ollama-r730.sh",
  "eval-ake-llama32-lora-r730.py",
  "eval-hosted-lab-chat-r730.py",
  "run-bitnet-lane-refresh-r730.sh",
  "run-full-pipeline-r730.sh",
  "resume-pipeline-r730.sh",
  "free-root-disk-r730.sh",
  "setup-r730-gpu-lane-policy-r730.sh",
  "fix-ninefold-bitnet-train-r730.sh",
  "setup-qvac-bitnet-gpu-r730.sh",
  "build-bitnet-specialist-prompts.py",
  "stabilize-hosted-inference-r730.sh",
  "post-train-ake-lora-r730.sh",
  "start-post-train-watcher-r730.sh",
  "prep-deploy-ake-lora-r730.sh",
  "smoke-bitnet-sidecar-r730.py",
  "setup-qvac-bitnet-build-r730.sh",
  "setup-bitnet-inference-build-r730.sh",
  "r730-hf-login.sh",
  "r730-hf-login-from-ninefold.sh",
  "setup-dual-inference-lanes-r730.sh",
  "build-bitnet-specialist-dataset.py",
  "setup-bitnet-train-env-r730.sh",
  "bitnet-qvac-model-path.sh",
  "r730-gpu-train-guard.sh",
  "train-bitnet-lora-r730.sh",
  "deploy-bitnet-finetuned-r730.sh",
  "build-ake-egregore-synthesis-blend.py",
  "build-bitnet-egregore-dataset.py",
  "train-ake-proper-blend-r730.sh",
  "train-bitnet-ninefold-r730.sh",
  "start-bitnet-ninefold-train-r730.sh",
  "deploy-bitnet-ninefold-r730.sh",
  "run-ninefold-proper-training-r730.sh",
  "export-egregorelab-inference-bundle.py",
  "train-bitnet-custom-egregore-r730.sh",
  "smoke-dual-lane-r730.sh",
  "post-ninefold-proper-r730.sh",
  "create-s2-ake-lora-r730.sh",
  "create-s2-ake-lora-from-merged-hf-r730.sh",
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

