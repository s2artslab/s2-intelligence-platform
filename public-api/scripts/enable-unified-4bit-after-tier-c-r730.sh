#!/usr/bin/env bash
# Wait for Tier C train to release GPU, then switch unified :8100 to 4-bit CUDA serve.
# Does not stop ComfyUI; requires ~10 GB free VRAM on P40 (24 GB total).
set -euo pipefail

API_DIR=/opt/s2-ecosystem/public-api
LOG=/var/log/s2-ake-tier-c-train.log
MIN_FREE_MIB="${MIN_FREE_MIB:-10240}"
POLL_SEC="${POLL_SEC:-30}"
MAX_WAIT_MIN="${MAX_WAIT_MIN:-180}"

gpu_free_mib() {
  nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' '
}

echo "=== Enable unified 4-bit after Tier C ==="
echo "Requires >= ${MIN_FREE_MIB} MiB GPU free (set MIN_FREE_MIB to override)"

if pgrep -f "train_egregore_on_foundation_7b.py ake" >/dev/null 2>&1; then
  echo "Tier C training still running — waiting (max ${MAX_WAIT_MIN} min)..."
  waited=0
  while pgrep -f "train_egregore_on_foundation_7b.py ake" >/dev/null 2>&1; do
    if [[ "$waited" -ge "$((MAX_WAIT_MIN * 60))" ]]; then
      echo "Timeout waiting for training. Still running — abort."
      exit 1
    fi
    sleep "$POLL_SEC"
    waited=$((waited + POLL_SEC))
    if [[ -f "$LOG" ]]; then
      tail -1 "$LOG" 2>/dev/null || true
    fi
  done
  echo "Training process ended."
else
  echo "No Tier C train process — continuing."
fi

if [[ -f "$LOG" ]] && ! grep -q "'epoch': 2" "$LOG" 2>/dev/null; then
  echo "WARN: log does not show epoch 2.0 complete — verify weights before serving."
fi

echo "Waiting for GPU headroom..."
for i in $(seq 1 40); do
  free="$(gpu_free_mib || echo 0)"
  echo "  GPU free: ${free} MiB (need ${MIN_FREE_MIB})"
  if [[ -n "$free" && "$free" -ge "$MIN_FREE_MIB" ]]; then
    break
  fi
  if [[ "$i" -eq 40 ]]; then
    echo "Insufficient VRAM. Stop ComfyUI or other GPU jobs, then re-run:"
    echo "  bash $API_DIR/scripts/setup-unified-4bit-r730.sh"
    exit 1
  fi
  sleep "$POLL_SEC"
done

bash "$API_DIR/scripts/setup-unified-4bit-r730.sh"

echo "--- quick generate smoke ---"
curl -sf -m 120 -X POST "http://127.0.0.1:8100/generate" \
  -H "Content-Type: application/json" \
  -d '{"egregore":"ake","prompt":"User question:\nWhat is deep key?\n\nAke:","max_length":80,"temperature":0.2,"use_persona":false}' \
  | head -c 400
echo ""
echo "Run eval gate when ready:"
echo "  python3 $API_DIR/scripts/tier-c-eval-gate-r730.py"
