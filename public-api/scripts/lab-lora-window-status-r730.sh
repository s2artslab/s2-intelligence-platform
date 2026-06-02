#!/usr/bin/env bash
# Quick status for lab LoRA window + GPU on r730.
set -euo pipefail

echo "=== Lab LoRA window status ==="
comfy_status="$(systemctl is-active comfyui.service 2>/dev/null)" || comfy_status="inactive"
echo "comfyui: $comfy_status"
echo "unified-egregore: $(systemctl is-active unified-egregore.service 2>/dev/null || echo unknown)"
echo "s2-public-api: $(systemctl is-active s2-public-api.service 2>/dev/null || echo unknown)"
if [[ -f /var/run/s2-lab-lora-window.state ]]; then
  cat /var/run/s2-lab-lora-window.state
else
  echo "lab window state: (no state file)"
fi
echo ""
echo "GPU:"
nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader 2>/dev/null || echo "nvidia-smi n/a"
echo ""
echo "Unified :8100 health:"
curl -sf -m 10 http://127.0.0.1:8100/health | python3 -m json.tool 2>/dev/null || curl -sf -m 10 http://127.0.0.1:8100/health || echo "unreachable"
echo ""
echo "Lab gateway health:"
curl -sf -m 10 http://127.0.0.1:3020/api/lab/unified-lora/health | python3 -m json.tool 2>/dev/null || echo "unreachable"
