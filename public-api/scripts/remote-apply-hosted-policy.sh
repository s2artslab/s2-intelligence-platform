#!/usr/bin/env bash
set -euo pipefail
COMFY_DROPIN=/etc/systemd/system/comfyui.service.d/gpu-media.conf
mkdir -p "$(dirname "$COMFY_DROPIN")"
cat >"$COMFY_DROPIN" <<'EOF'
# Managed by setup-r730-gpu-lane-policy-r730.sh — no Conflicts=ollama.service
[Unit]
After=network-online.target
Wants=network-online.target
EOF
systemctl daemon-reload
systemctl stop comfyui 2>/dev/null || true
systemctl mask --runtime comfyui 2>/dev/null || true
systemctl enable ollama 2>/dev/null || true
systemctl start ollama 2>/dev/null || true
systemctl start bitnet-sidecar 2>/dev/null || true
mkdir -p /var/lib/s2-ecosystem
echo hosted >/var/lib/s2-ecosystem/gpu-lane-mode
echo OK
cat "$COMFY_DROPIN"
systemctl is-active ollama comfyui
