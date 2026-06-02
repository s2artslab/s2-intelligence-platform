#!/usr/bin/env bash
# CPU-only QVAC Fabric build for BitNet LoRA (safe while GPU train runs).
#   nohup bash scripts/setup-qvac-bitnet-build-r730.sh >>/var/log/s2-qvac-bitnet-build.log 2>&1 &
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
QVAC_ROOT="${QVAC_ROOT:-/opt/qvac-fabric-llm.cpp}"
QVAC_DOCS="${QVAC_DOCS:-/opt/qvac-rnd-fabric-llm-bitnet}"
LOG="${LOG:-/var/log/s2-qvac-bitnet-build.log}"

bash "$API/scripts/setup-bitnet-train-env-r730.sh" >>"$LOG" 2>&1

if [[ ! -d "$QVAC_ROOT/.git" ]]; then
  echo "Cloning tetherto/qvac-fabric-llm.cpp → $QVAC_ROOT" | tee -a "$LOG"
  git clone --depth 1 https://github.com/tetherto/qvac-fabric-llm.cpp.git "$QVAC_ROOT" >>"$LOG" 2>&1
fi

cd "$QVAC_ROOT"
echo "=== $(date -Iseconds) QVAC build start ===" >>"$LOG"

if [[ -x "$QVAC_ROOT/build/bin/llama-finetune-lora" ]]; then
  echo "llama-finetune-lora already built" | tee -a "$LOG"
  exit 0
fi

if [[ -f Makefile ]]; then
  make -j"$(nproc)" >>"$LOG" 2>&1 || true
fi
if [[ ! -x "$QVAC_ROOT/build/bin/llama-finetune-lora" ]]; then
  cmake -B build >>"$LOG" 2>&1
  cmake --build build -j"$(nproc)" >>"$LOG" 2>&1
fi

if [[ -x "$QVAC_ROOT/build/bin/llama-finetune-lora" ]]; then
  echo "BUILD OK: $QVAC_ROOT/build/bin/llama-finetune-lora" | tee -a "$LOG"
else
  echo "BUILD INCOMPLETE — see $LOG" | tee -a "$LOG"
  exit 1
fi
