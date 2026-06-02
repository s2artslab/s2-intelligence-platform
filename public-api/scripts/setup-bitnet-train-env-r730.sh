#!/usr/bin/env bash
# BitNet b1.58 LoRA — clone QVAC Fabric (llama-finetune-lora) + deps on r730.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
QVAC_DOCS="${QVAC_DOCS:-/opt/qvac-rnd-fabric-llm-bitnet}"
QVAC_ROOT="${QVAC_ROOT:-/opt/qvac-fabric-llm.cpp}"
BITNET_ROOT="${BITNET_ROOT:-/opt/bitnet.cpp}"

echo "=== BitNet LoRA train environment ==="

if [[ ! -d "$BITNET_ROOT/.git" ]]; then
  echo "Cloning microsoft/BitNet → $BITNET_ROOT"
  git clone --depth 1 https://github.com/microsoft/BitNet.git "$BITNET_ROOT"
fi

if [[ ! -d "$QVAC_DOCS/.git" ]]; then
  echo "Cloning tetherto/qvac-rnd-fabric-llm-bitnet (research/docs) → $QVAC_DOCS"
  git clone --depth 1 https://github.com/tetherto/qvac-rnd-fabric-llm-bitnet.git "$QVAC_DOCS"
fi

if [[ ! -d "$QVAC_ROOT/.git" ]]; then
  echo "Cloning tetherto/qvac-fabric-llm.cpp (build + llama-finetune-lora) → $QVAC_ROOT"
  git clone --depth 1 https://github.com/tetherto/qvac-fabric-llm.cpp.git "$QVAC_ROOT"
else
  git -C "$QVAC_ROOT" pull --ff-only || true
fi

mkdir -p "$QVAC_ROOT/models" "$QVAC_ROOT/adapters" 2>/dev/null || true

if command -v hf >/dev/null 2>&1; then
  HF=hf
elif command -v huggingface-cli >/dev/null 2>&1; then
  HF=huggingface-cli
else
  echo "WARN: install huggingface-cli for model download"
  HF=""
fi

# QVAC finetune TQ2_0 (train); bitnet.cpp i2_s is for sidecar inference only.
QVAC_TQ2="${BITNET_MODEL_GGUF:-$QVAC_ROOT/models/BitNet-b1.58-2B-4T-tq2/dl-gianni-cor/bitnet_b1_58-xl-TQ2_0/bitnet_b1_58-xl-TQ2_0.gguf}"
I2S_GGUF="$BITNET_ROOT/models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf"
if [[ ! -f "$I2S_GGUF" ]] && [[ -n "$HF" ]]; then
  echo "Downloading BitNet b1.58 2B4T i2_s GGUF (bitnet.cpp inference)..."
  "$HF" download microsoft/bitnet-b1.58-2B-4T-gguf \
    --local-dir "$BITNET_ROOT/models/BitNet-b1.58-2B-4T" \
    --include "*.gguf" || true
fi
if [[ ! -f "$MODEL_GGUF" ]]; then
  echo "WARN: QVAC TQ2_0 GGUF missing — run: bash $API/scripts/convert-bitnet-tq2-r730.sh"
fi

echo ""
echo "Build llama-finetune-lora from qvac-fabric-llm.cpp (NOT the docs-only rnd repo):"
echo "  cd $QVAC_ROOT && cmake -B build && cmake --build build -j \$(nproc)"
echo ""
echo "Expected binary: $QVAC_ROOT/build/bin/llama-finetune-lora (path may vary)"
echo "Base model GGUF (QVAC train): $QVAC_TQ2"
echo "Sidecar inference GGUF: $I2S_GGUF"
echo "Dataset builder: python3 $API/scripts/build-bitnet-specialist-dataset.py"
