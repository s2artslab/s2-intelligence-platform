#!/usr/bin/env bash
# Create s2-ake-lora from merged HF weights (Ollama safetensors import).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGING="${OLLAMA_STAGING_DIR:-/root/ollama-s2-ake-lora}"
MERGED_HF="${MERGED_HF_PATH:-$STAGING/merged-hf}"
SRC="${MERGED_HF_SRC:-/mnt/bipra/egregore-training/trained_models/ake-llama32/gguf/merged-hf}"

if [[ ! -f "$MERGED_HF/model.safetensors.index.json" ]]; then
  if [[ ! -d "$SRC" ]]; then
    echo "ERROR: merged HF missing. Run merge_lora_to_gguf merge step first: $SRC"
    exit 1
  fi
  echo "Copying merged HF to Ollama staging on local disk ($MERGED_HF)..."
  rm -rf "$MERGED_HF"
  mkdir -p "$MERGED_HF"
  cp -a "$SRC/." "$MERGED_HF/"
fi

WORK="$STAGING/build"
rm -rf "$WORK"
mkdir -p "$WORK"

cat > "$WORK/Modelfile" <<EOF
FROM $MERGED_HF
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

echo "=== ollama create s2-ake-lora from merged HF ==="
( cd "$WORK" && ollama create s2-ake-lora -f Modelfile )
ollama list | grep s2-ake || true
