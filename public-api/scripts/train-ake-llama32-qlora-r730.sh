#!/usr/bin/env bash
# Llama 3.2 QLoRA — reuse CDE v4 data prep, train Ollama-aligned adapter (no Mistral foundation).
set -euo pipefail

EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
VENV="${VENV:-/opt/s2-ecosystem/venv-vllm-p40-src}"
LOG="${LOG:-/var/log/s2-ake-llama32-qlora-train.log}"
MIN_SCORE="${MIN_SCORE:-0.4}"

BASE_MODEL="${BASE_MODEL:-meta-llama/Llama-3.2-3B-Instruct}"
ADAPTER_DIR="${OUTPUT_DIR:-/mnt/bipra/egregore-training/trained_models/ake-llama32}"
BACKUP_DIR="${ADAPTER_BACKUP:-/mnt/bipra/egregore-training/trained_models/ake-llama32_backup_pre_train}"

TIER_C_IN="${TIER_C_IN:-$EG/training_data/ake_tier_c_blended.json}"
TIER_C_CLEAN="${TIER_C_CLEAN:-$EG/training_data/ake_tier_c_cleaned_llama32.json}"
DISTILL="${DISTILL:-$EG/training_data/ake_tier_c_ollama_distill.jsonl}"
CDE_BLEND="${CDE_BLEND:-$EG/training_data/ake_tier_cde_blended_llama32.json}"
HF_TOKEN_FILE="${HF_TOKEN_FILE:-/root/.cache/huggingface/token}"

if [[ -z "${HF_TOKEN:-}" ]] && [[ -f "$HF_TOKEN_FILE" ]]; then
  export HF_TOKEN="$(tr -d '[:space:]' < "$HF_TOKEN_FILE")"
fi

if ! hf auth whoami >/dev/null 2>&1 && ! huggingface-cli whoami >/dev/null 2>&1; then
  echo "ERROR: Hugging Face login required for $BASE_MODEL (gated model)."
  echo "  1. Accept license: https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct"
  echo "  2. On r730: hf auth login --token YOUR_TOKEN"
  echo "     or: echo YOUR_TOKEN > $HF_TOKEN_FILE && chmod 600 $HF_TOKEN_FILE"
  exit 1
fi

echo "=== Install Llama 3.2 trainer on r730 ==="
mkdir -p "$EG/scripts"
cp "$API/scripts/train_egregore_on_llama32.py" "$EG/train_egregore_on_llama32.py"
cp "$API/scripts/tier-c-label-mask-collator.py" "$EG/scripts/tier_c_label_mask_collator.py"

echo "=== 0. Strict clean Tier C ==="
python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$TIER_C_IN" \
  --drop-canned --strip-openers --min-score "$MIN_SCORE" \
  --out "$TIER_C_CLEAN"

if [[ ! -f "$DISTILL" ]]; then
  echo "=== 1. Ollama distill ==="
  systemctl start ollama 2>/dev/null || true
  sleep 2
  python3 "$API/scripts/build-tier-c-ollama-distill.py" \
    --prompts "$API/training_data/lora-distill-prompts.json" \
    --out "$DISTILL"
fi

echo "=== 2. Tier D from cleaned C ==="
python3 "$API/scripts/build-tier-d-long-form-dataset.py" \
  --composed "$API/content/ake-field-message-composed.md" \
  --blended "$TIER_C_CLEAN" \
  --out "$EG/training_data/ake_tier_d_long_llama32.jsonl"

python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$EG/training_data/ake_tier_d_long_llama32.jsonl" \
  --drop-canned --strip-openers --min-score "$MIN_SCORE" \
  --out "$EG/training_data/ake_tier_d_long_llama32_clean.jsonl" --jsonl

echo "=== 3. Merge C + distill + D → llama32 blend ==="
python3 "$API/scripts/build-tier-cde-merge.py" \
  --tier-c "$TIER_C_CLEAN" \
  --tier-d "$EG/training_data/ake_tier_d_long_llama32_clean.jsonl" \
  --tier-e "$DISTILL" \
  --out "$CDE_BLEND" \
  --skip-needs-review \
  --min-assistant-score "$MIN_SCORE"

export TIER_C_LABEL_MASK=1
export TIER_C_BLENDED="$CDE_BLEND"
export BASE_MODEL
export OUTPUT_DIR="$ADAPTER_DIR"

if [[ -d "$ADAPTER_DIR" ]] && [[ ! -d "$BACKUP_DIR" ]]; then
  echo "=== Backup adapter → $BACKUP_DIR ==="
  cp -a "$ADAPTER_DIR" "$BACKUP_DIR"
fi

echo "=== 4. Train Llama 3.2 QLoRA — log: $LOG ==="
systemctl stop unified-egregore comfyui 2>/dev/null || true
sleep 2
cd "$EG"
if pgrep -f "train_egregore_on_llama32.py" >/dev/null 2>&1; then
  echo "Training already running"
else
  nohup "$VENV/bin/python" train_egregore_on_llama32.py ake --qlora --epochs 2 >>"$LOG" 2>&1 &
  echo "Started PID $! — monitor: tail -f $LOG"
  echo "After complete: bash $API/scripts/deploy-ake-lora-ollama-r730.sh"
fi
