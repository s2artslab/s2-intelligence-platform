#!/usr/bin/env bash
# BitNet b1.58 LoRA fine-tune on specialist JSONL (QVAC Fabric / llama-finetune-lora).
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
QVAC_ROOT="${QVAC_ROOT:-/opt/qvac-fabric-llm.cpp}"
BITNET_ROOT="${BITNET_ROOT:-/opt/bitnet.cpp}"
LOG="${LOG:-/var/log/s2-bitnet-lora-train.log}"

DATASET="${BITNET_TRAIN_JSONL:-$EG/training_data/bitnet_specialist.jsonl}"
# shellcheck source=bitnet-qvac-model-path.sh
. "$API/scripts/bitnet-qvac-model-path.sh"
ADAPTER_OUT="${BITNET_LORA_OUT:-$EG/training_data/bitnet_ake_lora.gguf}"

LORA_RANK="${LORA_RANK:-8}"
LORA_ALPHA="${LORA_ALPHA:-16}"
CTX="${LORA_CTX:-256}"
BATCH="${LORA_BATCH:-32}"
EPOCHS="${LORA_EPOCHS:-3}"

bash "$API/scripts/setup-bitnet-train-env-r730.sh"

if [[ ! -f "$DATASET" ]]; then
  echo "=== Building specialist dataset ==="
  systemctl start ollama 2>/dev/null || true
  sleep 2
  python3 "$API/scripts/build-bitnet-specialist-dataset.py" \
    --prompts "$API/training_data/bitnet-specialist-prompts.json" \
    --out "$DATASET"
fi

FINETUNE=""
for candidate in \
  "$QVAC_ROOT/build/bin/llama-finetune-lora" \
  "$QVAC_ROOT/llama-finetune-lora" \
  "$QVAC_ROOT/bin/llama-finetune-lora"; do
  if [[ -x "$candidate" ]]; then
    FINETUNE="$candidate"
    break
  fi
done

if [[ -z "$FINETUNE" ]]; then
  echo "ERROR: llama-finetune-lora not found under $QVAC_ROOT"
  echo "Build QVAC Fabric per setup-bitnet-train-env-r730.sh, then re-run."
  exit 1
fi

if [[ ! -f "$MODEL_GGUF" ]]; then
  echo "ERROR: Base GGUF missing: $MODEL_GGUF"
  exit 1
fi

echo "=== BitNet LoRA train — log: $LOG ==="
# shellcheck source=r730-gpu-train-guard.sh
. "$API/scripts/r730-gpu-train-guard.sh"
r730_pause_comfyui_for_gpu_train

FINETUNE_ARGS=(
  -m "$MODEL_GGUF"
  -f "$DATASET"
  --output-adapter "$ADAPTER_OUT"
  --flash-attn off
  -c "$CTX"
  -b "$BATCH"
  --lora-rank "$LORA_RANK"
  --lora-alpha "$LORA_ALPHA"
  --num-epochs "$EPOCHS"
)
# llamacpp JSONL uses prompt/completion rows; chat JSONL needs --assistant-loss-only
if [[ "${BITNET_DATASET_FORMAT:-llamacpp}" == "chat" ]]; then
  FINETUNE_ARGS+=(--assistant-loss-only)
fi
# GPU offload when QVAC built with CUDA (P40)
if [[ "${BITNET_USE_GPU:-auto}" != "false" ]]; then
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    if "$FINETUNE" --help 2>&1 | grep -q 'gpu-layers'; then
      FINETUNE_ARGS+=(-ngl "${BITNET_NGL:-999}")
      echo "Using GPU layers: ${BITNET_NGL:-999}"
    fi
  fi
fi

{
  echo "=== $(date -Iseconds) BitNet LoRA ==="
  echo "model=$MODEL_GGUF dataset=$DATASET out=$ADAPTER_OUT format=${BITNET_DATASET_FORMAT:-llamacpp}"
  "$FINETUNE" "${FINETUNE_ARGS[@]}"
} >>"$LOG" 2>&1 &

echo "Started PID $! — monitor: tail -f $LOG"
echo "After complete: bash $API/scripts/deploy-bitnet-finetuned-r730.sh"
