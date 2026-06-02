#!/usr/bin/env bash
# CPU build for bitnet.cpp llama-cli (sidecar /generate). Safe while GPU QLoRA trains.
#   nohup bash scripts/setup-bitnet-inference-build-r730.sh >>/var/log/s2-bitnet-inference-build.log 2>&1 &
set -euo pipefail

BITNET_ROOT="${BITNET_ROOT:-/opt/bitnet.cpp}"
MODEL_DIR="${BITNET_MODEL_DIR:-$BITNET_ROOT/models/BitNet-b1.58-2B-4T}"
LOG="${LOG:-/var/log/s2-bitnet-inference-build.log}"
LLAMA_CLI="$BITNET_ROOT/build/bin/llama-cli"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

if [[ -x "$LLAMA_CLI" ]]; then
  log "llama-cli already built: $LLAMA_CLI"
  exit 0
fi

log "=== BitNet inference build start ==="

if ! command -v clang >/dev/null 2>&1 && ! command -v clang-19 >/dev/null 2>&1; then
  log "Installing clang-19..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq >>"$LOG" 2>&1
  apt-get install -y -qq clang-19 cmake build-essential git python3-pip >>"$LOG" 2>&1
fi

if command -v clang-19 >/dev/null 2>&1 && ! command -v clang >/dev/null 2>&1; then
  update-alternatives --install /usr/bin/clang clang /usr/bin/clang-19 100 >>"$LOG" 2>&1 || true
  update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-19 100 >>"$LOG" 2>&1 || true
fi

cd "$BITNET_ROOT"

if [[ ! -d 3rdparty/llama.cpp/.git ]]; then
  log "Initializing git submodules..."
  git submodule update --init --recursive >>"$LOG" 2>&1
fi

if [[ ! -f "$MODEL_DIR/ggml-model-i2_s.gguf" ]]; then
  log "WARN: GGUF missing at $MODEL_DIR/ggml-model-i2_s.gguf — setup_env may download/convert"
fi

log "Installing Python deps..."
python3 -m pip install -q --break-system-packages -r requirements.txt >>"$LOG" 2>&1 \
  || pip3 install -q --break-system-packages -r requirements.txt >>"$LOG" 2>&1

log "Running setup_env.py (codegen + cmake build)..."
export CC="${CC:-clang}"
export CXX="${CXX:-clang++}"
export PIP_BREAK_SYSTEM_PACKAGES=1
python3 -m pip install -q --break-system-packages "$BITNET_ROOT/3rdparty/llama.cpp/gguf-py" >>"$LOG" 2>&1 || true
# clang 19+ rejects const int8_t* → int8_t* in upstream ggml-bitnet-mad.cpp
sed -i 's/int8_t \* y_col = y + col \* by;/const int8_t * y_col = y + col * by;/' \
  "$BITNET_ROOT/src/ggml-bitnet-mad.cpp" 2>/dev/null || true
python3 setup_env.py -md "$MODEL_DIR" -q i2_s -ld /var/log/s2-bitnet-setup-env >>"$LOG" 2>&1
if [[ ! -x "$LLAMA_CLI" ]] && [[ -d "$BITNET_ROOT/build" ]]; then
  log "Retry cmake build after setup_env..."
  cmake --build "$BITNET_ROOT/build" -j"$(nproc)" >>"$LOG" 2>&1 || true
fi

if [[ -x "$LLAMA_CLI" ]]; then
  log "BUILD OK: $LLAMA_CLI"
  systemctl restart bitnet-sidecar || true
  exit 0
fi

log "BUILD INCOMPLETE — see $LOG and /var/log/s2-bitnet-setup-env/"
exit 1
