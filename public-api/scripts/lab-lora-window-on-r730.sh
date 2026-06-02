#!/usr/bin/env bash
# Lab LoRA window ON — free P40 for unified 4-bit Ake (:8100).
# Stops ComfyUI (files stay on /mnt/s2-data), ends stuck Tier C train if done, enables 4-bit CUDA.
# Restore Comfy after lab: lab-lora-window-off-r730.sh
set -euo pipefail

API_DIR=/opt/s2-ecosystem/public-api
STATE=/var/run/s2-lab-lora-window.state
TRAIN_LOG=/var/log/s2-ake-tier-c-train.log
TRAIN_PATTERN='train_egregore_on_foundation_7b.py ake'

echo "=== Lab LoRA window ON (unified 4-bit on P40) ==="

# Stop background enable watcher if still polling
pkill -f enable-unified-4bit-after-tier-c-r730.sh 2>/dev/null || true

if systemctl is-active --quiet comfyui.service; then
  echo "Stopping comfyui.service (models remain on /mnt/s2-data)..."
  systemctl stop comfyui.service
  echo "COMFY_WAS_ACTIVE=1" >"$STATE"
else
  echo "COMFY_WAS_ACTIVE=0" >"$STATE"
fi

if pgrep -f "$TRAIN_PATTERN" >/dev/null 2>&1; then
  if [[ -f "$TRAIN_LOG" ]] && grep -q "'epoch': 2" "$TRAIN_LOG" 2>/dev/null; then
    echo "Tier C train finished in log but process still running — sending SIGTERM..."
    pkill -f "$TRAIN_PATTERN" || true
    sleep 5
    pkill -9 -f "$TRAIN_PATTERN" 2>/dev/null || true
  else
    echo "ERROR: Tier C training still in progress. Wait or stop manually." >&2
    systemctl start comfyui.service 2>/dev/null || true
    exit 1
  fi
fi

echo "GPU after Comfy/train stop:"
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader 2>/dev/null || true

bash "$API_DIR/scripts/setup-unified-4bit-r730.sh"

echo ""
echo "--- health ---"
curl -sf "http://127.0.0.1:8100/health" | python3 -m json.tool 2>/dev/null || curl -sf "http://127.0.0.1:8100/health"
echo ""
echo "--- smoke generate (may take 60-120s first call) ---"
curl -sf -m 180 -X POST "http://127.0.0.1:8100/generate" \
  -H "Content-Type: application/json" \
  -d '{"egregore":"ake","prompt":"User question:\nSay hello in one sentence.\n\nAke:","max_length":60,"temperature":0.2,"use_persona":false}' \
  | head -c 500
echo ""
echo ""
echo "Lab UI: https://api.s2artslab.com/lab/ake-unified-lora"
echo "Status: bash $API_DIR/scripts/lab-lora-window-status-r730.sh"
echo "Eval: python3 $API_DIR/scripts/tier-c-eval-gate-r730.py --lab-chat --skip-gateway"
echo "When done: bash $API_DIR/scripts/lab-lora-window-off-r730.sh"
