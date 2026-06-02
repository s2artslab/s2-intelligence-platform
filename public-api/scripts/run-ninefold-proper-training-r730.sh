#!/usr/bin/env bash
# Ninefold proper training — Ake blend + BitNet egregore lanes.
#
#   bash scripts/run-ninefold-proper-training-r730.sh prepare   # datasets only
#   bash scripts/run-ninefold-proper-training-r730.sh ake       # Ake proper blend QLoRA
#   bash scripts/run-ninefold-proper-training-r730.sh bitnet    # 8 egregores @ 1.58-bit
#   bash scripts/run-ninefold-proper-training-r730.sh all       # prepare + queue both
#
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
CMD="${1:-prepare}"

case "$CMD" in
  prepare)
    echo "=== Ninefold proper training: prepare datasets ==="
    python3 "$API/scripts/build-ake-egregore-synthesis-blend.py" \
      --training-dir /opt/s2-ecosystem/egregore-training/training_data \
      --out /opt/s2-ecosystem/egregore-training/training_data/ake_tier_f_egregore_synthesis.jsonl \
      --per-egregore 400
    python3 "$API/scripts/build-bitnet-egregore-dataset.py" \
      --training-dir /opt/s2-ecosystem/egregore-training/training_data \
      --out-dir /opt/s2-ecosystem/egregore-training/training_data/bitnet_egregores \
      --per-egregore 800
    bash "$API/scripts/setup-bitnet-train-env-r730.sh"
    echo ""
    echo "Next:"
    echo "  bash $API/scripts/train-ake-proper-blend-r730.sh   # after current Llama32 train"
    echo "  bash $API/scripts/train-bitnet-ninefold-r730.sh      # needs QVAC llama-finetune-lora"
    ;;
  ake)
    bash "$API/scripts/train-ake-proper-blend-r730.sh"
    ;;
  bitnet)
    bash "$API/scripts/train-bitnet-ninefold-r730.sh"
    bash "$API/scripts/deploy-bitnet-ninefold-r730.sh" || true
    ;;
  all)
    bash "$0" prepare
    bash "$0" ake
    bash "$0" bitnet
    ;;
  *)
    echo "Usage: $0 {prepare|ake|bitnet|all}"
    exit 1
    ;;
esac
