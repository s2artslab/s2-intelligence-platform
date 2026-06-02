#!/usr/bin/env bash
# Convert BitNet b1.58 HF weights to TQ2_0 GGUF for QVAC llama-finetune-lora.
set -euo pipefail

QVAC_ROOT="${QVAC_ROOT:-/opt/qvac-fabric-llm.cpp}"
OUT_DIR="${BITNET_TQ2_DIR:-$QVAC_ROOT/models/BitNet-b1.58-2B-4T-tq2}"
OUT_GGUF="${BITNET_MODEL_GGUF:-$OUT_DIR/ggml-model-tq2_0.gguf}"
HF_MODEL="${BITNET_HF_MODEL:-microsoft/BitNet-b1.58-2B-4T}"
PYTHON="${PYTHON:-python3}"
LOG="${LOG:-/var/log/s2-bitnet-tq2-convert.log}"

mkdir -p "$OUT_DIR"

if [[ -f "$OUT_GGUF" ]]; then
  echo "TQ2_0 GGUF already exists: $OUT_GGUF"
  exit 0
fi

echo "=== Convert BitNet HF → TQ2_0 GGUF ===" | tee -a "$LOG"
echo "HF: $HF_MODEL" | tee -a "$LOG"
echo "Out: $OUT_GGUF" | tee -a "$LOG"

HF_CACHE="${HF_HOME:-/root/.cache/huggingface}/hub"
if ! "$PYTHON" -c "import transformers" 2>/dev/null; then
  echo "Installing transformers for convert..."
  "$PYTHON" -m pip install -q transformers sentencepiece
fi

{
  cd "$QVAC_ROOT"
  "$PYTHON" convert_hf_to_gguf.py \
    "$HF_MODEL" \
    --outfile "$OUT_GGUF" \
    --outtype tq2_0
} >>"$LOG" 2>&1

if [[ ! -f "$OUT_GGUF" ]]; then
  echo "ERROR: convert failed — see $LOG"
  tail -30 "$LOG"
  exit 1
fi

ls -lh "$OUT_GGUF"
echo "Done. Train with:"
echo "  BITNET_MODEL_GGUF=$OUT_GGUF bash /opt/s2-ecosystem/public-api/scripts/train-bitnet-lora-r730.sh"
