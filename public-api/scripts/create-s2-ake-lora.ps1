# Create s2-ake-lora on r730 via SSH (adapter or merged GGUF).
#
#   .\scripts\create-s2-ake-lora.ps1 -Mode adapter
#   .\scripts\create-s2-ake-lora.ps1 -Mode gguf -GgufPath /opt/.../s2-ake-lora-q4_k_m.gguf

param(
  [ValidateSet("adapter", "gguf")]
  [string]$Mode = "adapter",
  [string]$SshHost = "192.168.1.78",
  [string]$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_proxmox",
  [string]$RemoteApiDir = "/opt/s2-ecosystem/s2-intelligence-public-api",
  [string]$LoraAdapterPath = "/opt/s2-ecosystem/egregore-training/ake/models/lora",
  [string]$GgufPath = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "Syncing public-api ollama scripts to r730..."
ssh -i $SshKey "root@$SshHost" "mkdir -p $RemoteApiDir"
scp -i $SshKey -r "$root\ollama" "root@${SshHost}:${RemoteApiDir}/"
ssh -i $SshKey "root@$SshHost" "mkdir -p ${RemoteApiDir}/scripts"
scp -i $SshKey "$root\scripts\create-s2-ake-lora-r730.sh" "root@${SshHost}:${RemoteApiDir}/scripts/"

$script = "${RemoteApiDir}/scripts/create-s2-ake-lora-r730.sh"
if ($Mode -eq "adapter") {
  ssh -i $SshKey "root@$SshHost" "chmod +x $script; LORA_ADAPTER_PATH=$LoraAdapterPath bash $script --adapter"
} else {
  if (-not $GgufPath) { throw "GgufPath required for -Mode gguf" }
  ssh -i $SshKey "root@$SshHost" "chmod +x $script; bash $script --gguf $GgufPath"
}

Write-Host "Done. Set OLLAMA_LORA_MODEL=s2-ake-lora and OLLAMA_PREFER_LORA=true on public-api."
