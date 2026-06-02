#!/usr/bin/env bash
# Train BitNet b1.58 LoRA for one EgregoreLab (user-generated) egregore.
# Usage: EGREGORE_ID=my_agent bash scripts/train-bitnet-custom-egregore-r730.sh
set -euo pipefail

EGREGORE_ID="${EGREGORE_ID:-}"
if [[ -z "$EGREGORE_ID" ]]; then
  echo "Usage: EGREGORE_ID=<id> $0"
  exit 1
fi

EGREGORE_ID="$(echo "$EGREGORE_ID" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')"

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
QVAC_ROOT="${QVAC_ROOT:-/opt/qvac-fabric-llm.cpp}"
BITNET_ROOT="${BITNET_ROOT:-/opt/bitnet.cpp}"
LOG="${LOG:-/var/log/s2-bitnet-custom-${EGREGORE_ID}-train.log}"

DATA_DIR="${BITNET_EGREGORE_DATA:-$EG/training_data/bitnet_egregores}"
ADAPTER_DIR="${BITNET_ADAPTER_DIR:-$EG/training_data/bitnet_adapters}"
PROFILES="${EGREGORE_PROFILES_PATH:-/opt/s2-ecosystem/ninefold-studio-clean/egregorelab/config/unified_egregore_profiles.json}"
# shellcheck source=bitnet-qvac-model-path.sh
. "$API/scripts/bitnet-qvac-model-path.sh"

LORA_RANK="${LORA_RANK:-8}"
LORA_ALPHA="${LORA_ALPHA:-16}"
CTX="${LORA_CTX:-256}"
BATCH="${LORA_BATCH:-32}"
EPOCHS="${LORA_EPOCHS:-3}"

echo "=== Export EgregoreLab bundle: $EGREGORE_ID ===" | tee -a "$LOG"
python3 "$API/scripts/export-egregorelab-inference-bundle.py" \
  --profiles "$PROFILES" \
  --out-dir "$DATA_DIR" \
  --manifest "$EG/training_data/egregore_inference_manifest.json" \
  --registry "$ADAPTER_DIR/bitnet_egregore_registry.json" \
  --egregore "$EGREGORE_ID" \
  --per-egregore "${PER_EGREGORE:-400}" >>"$LOG" 2>&1

DATASET="$DATA_DIR/bitnet_${EGREGORE_ID}.jsonl"
ADAPTER_OUT="$ADAPTER_DIR/bitnet_${EGREGORE_ID}_lora.gguf"
if [[ ! -f "$DATASET" ]]; then
  echo "ERROR: dataset missing: $DATASET"
  exit 1
fi

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
  echo "ERROR: llama-finetune-lora not found under $QVAC_ROOT"
  exit 1
fi

if [[ ! -f "$MODEL_GGUF" ]]; then
  echo "ERROR: Base GGUF missing: $MODEL_GGUF"
  exit 1
fi

mkdir -p "$ADAPTER_DIR"
# shellcheck source=r730-gpu-train-guard.sh
. "$API/scripts/r730-gpu-train-guard.sh"
r730_pause_comfyui_for_gpu_train

echo "=== Train BitNet LoRA: $EGREGORE_ID ===" | tee -a "$LOG"
{
  echo "=== $(date -Iseconds) $EGREGORE_ID ==="
  "$FINETUNE" \
    -m "$MODEL_GGUF" \
    -f "$DATASET" \
    --output-adapter "$ADAPTER_OUT" \
    --flash-attn off \
    -c "$CTX" \
    -b "$BATCH" \
    --lora-rank "$LORA_RANK" \
    --lora-alpha "$LORA_ALPHA" \
    --num-epochs "$EPOCHS"
} >>"$LOG" 2>&1

if [[ ! -f "$ADAPTER_OUT" ]]; then
  echo "FAIL — see $LOG"
  exit 1
fi

REGISTRY="$ADAPTER_DIR/bitnet_egregore_registry.json"
python3 - <<PY
import json
from pathlib import Path
reg = Path("$REGISTRY")
data = json.loads(reg.read_text()) if reg.is_file() else {}
data["$EGREGORE_ID"] = "$ADAPTER_OUT"
reg.write_text(json.dumps(data, indent=2))
manifest = Path("$EG/training_data/egregore_inference_manifest.json")
if manifest.is_file():
    m = json.loads(manifest.read_text())
    m.setdefault("egregores", {}).setdefault("$EGREGORE_ID", {})["bitnet_adapter"] = "$ADAPTER_OUT"
    m["egregores"]["$EGREGORE_ID"]["lanes"] = {"hosted": True, "bitnet": True}
    manifest.write_text(json.dumps(m, indent=2))
PY

echo "OK $EGREGORE_ID → $ADAPTER_OUT"
bash "$API/scripts/deploy-bitnet-ninefold-r730.sh" >>"$LOG" 2>&1 || true
systemctl start bitnet-sidecar 2>/dev/null || true
echo "Restart gateway if needed: systemctl restart s2-public-api"
