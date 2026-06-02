#!/usr/bin/env bash
# Lab LoRA window OFF — return unified to CPU lab mode, restart Comfy if it was running.
set -euo pipefail

API_DIR=/opt/s2-ecosystem/public-api
STATE=/var/run/s2-lab-lora-window.state

echo "=== Lab LoRA window OFF ==="

bash "$API_DIR/scripts/setup-unified-production-r730.sh"

if [[ -f "$STATE" ]] && grep -q '^COMFY_WAS_ACTIVE=1' "$STATE"; then
  echo "Restarting comfyui.service..."
  systemctl start comfyui.service
elif [[ ! -f "$STATE" ]]; then
  echo "No state file — starting ComfyUI anyway (was likely active before lab window)."
  systemctl start comfyui.service
else
  echo "ComfyUI was not active before lab window — leaving stopped."
fi

rm -f "$STATE"
echo "Done. Comfy: $(systemctl is-active comfyui.service 2>/dev/null || echo unknown)"
echo "Unified :8100: CPU production-safe mode"
