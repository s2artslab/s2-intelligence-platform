#!/usr/bin/env bash
# Create s2-ake-lora in Ollama on r730.
#
#   bash scripts/create-s2-ake-lora-r730.sh --adapter
#   bash scripts/create-s2-ake-lora-r730.sh --gguf /path/to/s2-ake-lora-q4_k_m.gguf
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LORA_ADAPTER_PATH="${LORA_ADAPTER_PATH:-/opt/s2-ecosystem/egregore-training/ake/models/lora}"
MODE=""
GGUF_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --adapter) MODE="adapter"; shift ;;
    --gguf) MODE="gguf"; GGUF_PATH="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if [[ -z "$MODE" ]]; then
  echo "Usage: $0 --adapter | --gguf /path/to/model.gguf"
  exit 1
fi

if [[ "$MODE" == "adapter" ]]; then
  if [[ ! -f "$LORA_ADAPTER_PATH/adapter_config.json" ]]; then
    echo "ERROR: LoRA adapter not found at $LORA_ADAPTER_PATH"
    echo "Train first, then re-run with LORA_ADAPTER_PATH=..."
    exit 1
  fi
  WORK="$ROOT/ollama/build-s2-ake-lora-adapter"
  rm -rf "$WORK"
  mkdir -p "$WORK/lora-adapter"
  cp "$LORA_ADAPTER_PATH/adapter_config.json" "$LORA_ADAPTER_PATH/adapter_model.safetensors" \
    "$WORK/lora-adapter/"
  cat > "$WORK/Modelfile" <<EOF
FROM llama3.2
ADAPTER ./lora-adapter
PARAMETER temperature 0.35
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.08
PARAMETER num_ctx 8192
PARAMETER num_predict 2048
SYSTEM """You are the S² assistant: clear, practical, and accurate.
You help users with organized, step-by-step guidance. You do not pretend to be multiple people.
When you lack information, say so. For legal topics you provide information, not legal advice.
Prefer structured answers with headings when it helps scanning."""
EOF
  ( cd "$WORK" && ollama create s2-ake-lora -f Modelfile )
elif [[ "$MODE" == "gguf" ]]; then
  if [[ ! -f "$GGUF_PATH" ]]; then
    echo "ERROR: GGUF not found: $GGUF_PATH"
    exit 1
  fi
  WORK="$ROOT/ollama/build-s2-ake-lora-gguf"
  rm -rf "$WORK"
  mkdir -p "$WORK"
  ln -sf "$(realpath "$GGUF_PATH")" "$WORK/model.gguf"
  cat > "$WORK/Modelfile" <<'EOF'
FROM ./model.gguf
PARAMETER temperature 0.35
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.08
PARAMETER num_ctx 8192
PARAMETER num_predict 2048
SYSTEM """You are the S² assistant: clear, practical, and accurate.
You help users with organized, step-by-step guidance. You do not pretend to be multiple people.
When you lack information, say so. For legal topics you provide information, not legal advice.
Prefer structured answers with headings when it helps scanning."""
EOF
  ( cd "$WORK" && ollama create s2-ake-lora -f Modelfile )
fi

echo "Created:"
ollama list | grep s2-ake || true
