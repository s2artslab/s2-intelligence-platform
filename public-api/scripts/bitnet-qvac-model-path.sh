#!/usr/bin/env bash
# Resolve QVAC-compatible BitNet b1.58 TQ2_0 GGUF for llama-finetune-lora (not bitnet.cpp i2_s).
# Source from train scripts: . "$(dirname "$0")/bitnet-qvac-model-path.sh"

QVAC_ROOT="${QVAC_ROOT:-/opt/qvac-fabric-llm.cpp}"
BITNET_ROOT="${BITNET_ROOT:-/opt/bitnet.cpp}"

BITNET_MODEL_GGUF="${BITNET_MODEL_GGUF:-$QVAC_ROOT/models/BitNet-b1.58-2B-4T-tq2/bitnet_b1_58-xl-TQ2_0.gguf}"
if [[ ! -f "$BITNET_MODEL_GGUF" ]]; then
  _alt="$QVAC_ROOT/models/BitNet-b1.58-2B-4T-tq2/dl-gianni-cor/bitnet_b1_58-xl-TQ2_0/bitnet_b1_58-xl-TQ2_0.gguf"
  [[ -f "$_alt" ]] && BITNET_MODEL_GGUF="$_alt"
fi
MODEL_GGUF="${MODEL_GGUF:-$BITNET_MODEL_GGUF}"

if [[ ! -f "$MODEL_GGUF" ]]; then
  echo "ERROR: QVAC BitNet GGUF missing. Set BITNET_MODEL_GGUF or run convert-bitnet-tq2-r730.sh"
  echo "  Tried: $BITNET_MODEL_GGUF"
  exit 1
fi
if [[ "$MODEL_GGUF" == *i2_s* ]] || [[ "$MODEL_GGUF" == *i2* && "$MODEL_GGUF" != *TQ2* ]]; then
  echo "ERROR: $MODEL_GGUF is bitnet.cpp i2_s — QVAC llama-finetune-lora requires TQ2_0 GGUF."
  exit 1
fi
export BITNET_MODEL_GGUF MODEL_GGUF
