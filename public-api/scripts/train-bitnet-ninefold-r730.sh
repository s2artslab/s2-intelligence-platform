#!/usr/bin/env bash
# Train BitNet b1.58 LoRA for each Ninefold specialist (8 egregores).
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
QVAC_ROOT="${QVAC_ROOT:-/opt/qvac-fabric-llm.cpp}"
BITNET_ROOT="${BITNET_ROOT:-/opt/bitnet.cpp}"
LOG="${LOG:-/var/log/s2-bitnet-ninefold-train.log}"

DATA_DIR="${BITNET_EGREGORE_DATA:-$EG/training_data/bitnet_egregores}"
ADAPTER_DIR="${BITNET_ADAPTER_DIR:-$EG/training_data/bitnet_adapters}"
# shellcheck source=bitnet-qvac-model-path.sh
. "$API/scripts/bitnet-qvac-model-path.sh"

LORA_RANK="${LORA_RANK:-8}"
LORA_ALPHA="${LORA_ALPHA:-16}"
CTX="${LORA_CTX:-256}"
BATCH="${LORA_BATCH:-32}"
EPOCHS="${LORA_EPOCHS:-3}"

EGREGORES="${NINEFOLD_EGREGORES:-rhys,ketheriel,wraith,flux,chalyth,kairos,seraphel,vireon}"

bash "$API/scripts/setup-bitnet-train-env-r730.sh"

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
  echo "=== Building QVAC llama-finetune-lora ==="
  if [[ -d "$QVAC_ROOT" ]]; then
    (cd "$QVAC_ROOT" && (make -j"$(nproc)" 2>/dev/null || (cmake -B build && cmake --build build -j"$(nproc)"))) >>"$LOG" 2>&1 || true
  fi
  for candidate in \
    "$QVAC_ROOT/build/bin/llama-finetune-lora" \
    "$QVAC_ROOT/build/llama-finetune-lora"; do
    if [[ -x "$candidate" ]]; then
      FINETUNE="$candidate"
      break
    fi
  done
fi

if [[ -z "$FINETUNE" ]]; then
  echo "ERROR: llama-finetune-lora not built under $QVAC_ROOT"
  echo "Build manually, then re-run. See setup-bitnet-train-env-r730.sh"
  exit 1
fi

if [[ ! -f "$MODEL_GGUF" ]]; then
  echo "ERROR: Base GGUF missing: $MODEL_GGUF"
  exit 1
fi

echo "=== Build compact egregore datasets ==="
python3 "$API/scripts/build-bitnet-egregore-dataset.py" \
  --training-dir "$EG/training_data" \
  --out-dir "$DATA_DIR" \
  --per-egregore 800 \
  --min-score "${BITNET_EGREGORE_MIN_SCORE:-0.5}"

mkdir -p "$ADAPTER_DIR"
REGISTRY="$ADAPTER_DIR/bitnet_egregore_registry.json"
if [[ -f "$REGISTRY" ]]; then
  cp "$REGISTRY" "$REGISTRY.tmp"
else
  echo "{}" >"$REGISTRY.tmp"
fi

# shellcheck source=r730-gpu-train-guard.sh
. "$API/scripts/r730-gpu-train-guard.sh"

_bitnet_use_gpu_effective() {
  case "${BITNET_USE_GPU:-auto}" in
    false|0|no|cpu) echo false ;;
    true|1|yes|gpu) echo true ;;
    *)
      # QVAC llama-finetune-lora -ngl hits CUBLAS_STATUS_INVALID_VALUE on Tesla P40 (sm_61)
      if nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -qiE 'P40|Tesla P'; then
        echo false
      else
        echo true
      fi
      ;;
  esac
}

_BITNET_GPU="$(_bitnet_use_gpu_effective)"
if [[ "$_BITNET_GPU" == "false" ]]; then
  export CUDA_VISIBLE_DEVICES="${BITNET_TRAIN_CUDA_VISIBLE:-}"
  r730_pause_comfyui_for_gpu_train
  echo "BitNet train mode: CPU (BITNET_USE_GPU=${BITNET_USE_GPU:-auto})" | tee -a "$LOG"
else
  r730_prepare_p40_for_bitnet_train
  unset CUDA_VISIBLE_DEVICES
  echo "BitNet train: GPU (-ngl ${BITNET_NGL:-999})" | tee -a "$LOG"
fi

_bitnet_finetune_args() {
  local dataset="$1" adapter_out="$2"
  FINETUNE_ARGS=(
    -m "$MODEL_GGUF"
    -f "$dataset"
    --output-adapter "$adapter_out"
    --flash-attn off
    -c "$CTX"
    -b "$BATCH"
    --lora-rank "$LORA_RANK"
    --lora-alpha "$LORA_ALPHA"
    --num-epochs "$EPOCHS"
  )
  if [[ "$_BITNET_GPU" == "true" ]]; then
    if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
      if "$FINETUNE" --help 2>&1 | grep -q 'gpu-layers'; then
        FINETUNE_ARGS+=(-ngl "${BITNET_NGL:-999}")
        echo "Using GPU layers: ${BITNET_NGL:-999}" | tee -a "$LOG"
      fi
    fi
  else
    echo "CPU train (BITNET_USE_GPU=false)" | tee -a "$LOG"
  fi
}

IFS=',' read -ra EG_LIST <<<"$EGREGORES"
for eg in "${EG_LIST[@]}"; do
  eg="$(echo "$eg" | tr -d '[:space:]')"
  DATASET="$DATA_DIR/bitnet_${eg}.jsonl"
  ADAPTER_OUT="$ADAPTER_DIR/bitnet_${eg}_lora.gguf"
  if [[ ! -f "$DATASET" ]]; then
    echo "WARN skip $eg — no dataset"
    continue
  fi
  if [[ -f "$ADAPTER_OUT" ]] && [[ "${FORCE_RETRAIN:-0}" != "1" ]]; then
    echo "SKIP $eg — adapter exists ($ADAPTER_OUT); set FORCE_RETRAIN=1 to retrain" | tee -a "$LOG"
    python3 - <<PY
import json
from pathlib import Path
reg = Path("$REGISTRY.tmp")
data = json.loads(reg.read_text()) if reg.stat().st_size > 2 else {}
data["$eg"] = "$ADAPTER_OUT"
reg.write_text(json.dumps(data, indent=2))
PY
    continue
  fi
  echo "=== Train BitNet LoRA: $eg ===" | tee -a "$LOG"
  _bitnet_finetune_args "$DATASET" "$ADAPTER_OUT"
  {
    echo "=== $(date -Iseconds) $eg ==="
    "$FINETUNE" "${FINETUNE_ARGS[@]}"
  } >>"$LOG" 2>&1
  if [[ -f "$ADAPTER_OUT" ]]; then
    python3 - <<PY
import json
from pathlib import Path
reg = Path("$REGISTRY.tmp")
data = json.loads(reg.read_text()) if reg.stat().st_size > 2 else {}
data["$eg"] = "$ADAPTER_OUT"
reg.write_text(json.dumps(data, indent=2))
PY
    echo "OK $eg → $ADAPTER_OUT"
  else
    echo "FAIL $eg — see $LOG"
  fi
done

mv "$REGISTRY.tmp" "$REGISTRY"
if [[ "$_BITNET_GPU" == "true" ]]; then
  r730_restore_hosted_after_bitnet_train
fi
echo "Registry: $REGISTRY"
echo "Deploy: bash $API/scripts/deploy-bitnet-ninefold-r730.sh"
