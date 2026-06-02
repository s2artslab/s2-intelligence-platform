#!/usr/bin/env bash
# Master entry: dual inference lanes on r730 (Llama 3.2 QLoRA + BitNet specialist LoRA).
#
#   bash scripts/setup-dual-inference-lanes-r730.sh prepare   # data + env only
#   bash scripts/setup-dual-inference-lanes-r730.sh llama      # full Llama QLoRA train (background)
#   bash scripts/setup-dual-inference-lanes-r730.sh bitnet     # BitNet LoRA train (background)
#   bash scripts/setup-dual-inference-lanes-r730.sh deploy     # after trains complete
#
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
CMD="${1:-prepare}"

case "$CMD" in
  prepare)
    echo "=== Dual lanes: prepare datasets + train env ==="
    bash "$API/scripts/setup-bitnet-train-env-r730.sh"
    systemctl start ollama 2>/dev/null || true
    sleep 2
    python3 "$API/scripts/build-bitnet-specialist-dataset.py" \
      --prompts "$API/training_data/bitnet-specialist-prompts.json" \
      --out /opt/s2-ecosystem/egregore-training/training_data/bitnet_specialist.jsonl \
      || echo "WARN: BitNet dataset build skipped (Ollama down?)"
    echo "Llama lane: run 'bash $API/scripts/train-ake-llama32-qlora-r730.sh'"
    echo "BitNet lane: run 'bash $API/scripts/train-bitnet-lora-r730.sh'"
    ;;
  llama)
    bash "$API/scripts/train-ake-llama32-qlora-r730.sh"
    ;;
  bitnet)
    bash "$API/scripts/train-bitnet-lora-r730.sh"
    ;;
  deploy)
    echo "=== Deploy both lanes (requires completed training) ==="
    bash "$API/scripts/deploy-ake-lora-ollama-r730.sh" || echo "WARN: Llama deploy failed"
    bash "$API/scripts/deploy-bitnet-finetuned-r730.sh" || echo "WARN: BitNet deploy failed"
    ;;
  *)
    echo "Usage: $0 {prepare|llama|bitnet|deploy}"
    exit 1
    ;;
esac
