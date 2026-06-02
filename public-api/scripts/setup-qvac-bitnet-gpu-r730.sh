#!/usr/bin/env bash
# Rebuild QVAC Fabric with CUDA for BitNet GPU train/inference (r730 Tesla P40 sm_61).
# Run when GPU is free (stop ComfyUI / unified-egregore if needed).
set -euo pipefail

QVAC_ROOT="${QVAC_ROOT:-/opt/qvac-fabric-llm.cpp}"
LOG="${LOG:-/var/log/s2-qvac-bitnet-gpu-build.log}"
CUDA_ARCH="${CUDA_ARCH:-61}"

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
bash "$API/scripts/setup-bitnet-train-env-r730.sh" >>"$LOG" 2>&1 || true

if ! command -v nvcc >/dev/null 2>&1; then
  echo "WARN: nvcc not in PATH — install cuda-toolkit or ensure /usr/local/cuda/bin is on PATH"
fi

echo "=== $(date -Iseconds) QVAC GPU rebuild ===" | tee -a "$LOG"
systemctl stop comfyui unified-egregore 2>/dev/null || true

cd "$QVAC_ROOT"
rm -rf build
{
  cmake -B build \
    -DGGML_CUDA=ON \
    -DCMAKE_CUDA_ARCHITECTURES="$CUDA_ARCH" \
    -DLLAMA_CURL=ON
  cmake --build build -j "$(nproc)"
} >>"$LOG" 2>&1

for bin in llama-cli llama-finetune-lora; do
  if [[ ! -x "$QVAC_ROOT/build/bin/$bin" ]]; then
    echo "ERROR: missing $QVAC_ROOT/build/bin/$bin — see $LOG"
    tail -40 "$LOG"
    exit 1
  fi
done

echo "=== GPU smoke ===" | tee -a "$LOG"
"$QVAC_ROOT/build/bin/llama-cli" --version 2>&1 | tee -a "$LOG" || true

TQ2="${BITNET_QVAC_MODEL:-$QVAC_ROOT/models/BitNet-b1.58-2B-4T-tq2/dl-gianni-cor/bitnet_b1_58-xl-TQ2_0/bitnet_b1_58-xl-TQ2_0.gguf}"
if [[ -f "$TQ2" ]]; then
  "$QVAC_ROOT/build/bin/llama-cli" -m "$TQ2" -ngl 99 -p "Hi" -n 1 --flash-attn off --no-display-prompt 2>&1 | tee -a "$LOG" || true
fi

echo "BUILD OK (CUDA): $QVAC_ROOT/build/bin/llama-cli"
echo "Log: $LOG"
