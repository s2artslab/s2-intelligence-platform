#!/usr/bin/env bash
# Watch BitNet LoRA train log; deploy adapter when complete.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
LOG="${LOG:-/var/log/s2-bitnet-lora-train.log}"
ADAPTER="${BITNET_LORA_OUT:-$EG/training_data/bitnet_ake_lora.gguf}"
POLL="${POLL_SEC:-30}"

echo "Watching $LOG for BitNet LoRA completion..."
while true; do
  if [[ -f "$ADAPTER" ]]; then
    echo "Adapter ready: $ADAPTER"
    bash "$API/scripts/deploy-bitnet-finetuned-r730.sh"
    python3 "$API/scripts/smoke-bitnet-sidecar-r730.py" || true
    bash "$API/scripts/stabilize-hosted-inference-r730.sh"
    exit 0
  fi
  if grep -qE 'Training complete|successfully|Saved adapter|error:|Segmentation fault|Failed to create dataset' "$LOG" 2>/dev/null; then
    if [[ -f "$ADAPTER" ]]; then
      bash "$API/scripts/deploy-bitnet-finetuned-r730.sh"
      exit 0
    fi
    echo "Train ended without adapter — see $LOG"
    tail -30 "$LOG"
    exit 1
  fi
  sleep "$POLL"
done
