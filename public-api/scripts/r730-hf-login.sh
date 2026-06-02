#!/usr/bin/env bash
# Log in to Hugging Face on r730 (required for meta-llama/Llama-3.2-3B-Instruct QLoRA).
#
#   HF_TOKEN=hf_xxx bash scripts/r730-hf-login.sh
#   bash scripts/r730-hf-login.sh hf_xxx
#
set -euo pipefail

TOKEN="${HF_TOKEN:-${1:-}}"
HF_TOKEN_FILE="${HF_TOKEN_FILE:-/root/.cache/huggingface/token}"

if [[ -z "$TOKEN" ]]; then
  echo "Usage: HF_TOKEN=hf_xxx bash $0"
  echo "Accept license first: https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct"
  exit 1
fi

mkdir -p "$(dirname "$HF_TOKEN_FILE")"
printf '%s' "$TOKEN" > "$HF_TOKEN_FILE"
chmod 600 "$HF_TOKEN_FILE"
export HF_TOKEN="$TOKEN"

if command -v hf >/dev/null 2>&1; then
  hf auth login --token "$TOKEN"
  hf auth whoami
elif command -v huggingface-cli >/dev/null 2>&1; then
  huggingface-cli login --token "$TOKEN"
  huggingface-cli whoami
else
  echo "WARN: hf CLI not found; token written to $HF_TOKEN_FILE"
fi

echo "OK — re-run: bash /opt/s2-ecosystem/public-api/scripts/train-ake-llama32-qlora-r730.sh"
