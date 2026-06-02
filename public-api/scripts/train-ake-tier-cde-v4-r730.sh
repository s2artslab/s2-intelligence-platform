#!/usr/bin/env bash
# CDE v4 — drop-before-strip C, Ollama distill blend, strict min-score 0.4, QLoRA + label mask.
set -euo pipefail

EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
APPS_ROOT="${S2_APPS_ROOT:-/opt/s2-ecosystem}"
VENV="${VENV:-/opt/s2-ecosystem/venv-vllm-p40-src}"
LOG="${LOG:-/var/log/s2-ake-tier-cde-v4-train.log}"
MIN_SCORE="${MIN_SCORE:-0.4}"

TIER_C_IN="${TIER_C_IN:-$EG/training_data/ake_tier_c_blended.json}"
TIER_C_CLEAN="${TIER_C_CLEAN:-$EG/training_data/ake_tier_c_cleaned_v4.json}"
DISTILL="${DISTILL:-$EG/training_data/ake_tier_c_ollama_distill.jsonl}"
CDE_BLEND="${CDE_BLEND:-$EG/training_data/ake_tier_cde_blended_v4.json}"
ADAPTER_DIR="${OUTPUT_DIR:-/mnt/bipra/egregore-training/trained_models/ake}"
BACKUP_DIR="${ADAPTER_BACKUP:-/mnt/bipra/egregore-training/trained_models/ake_backup_pre_cde_v4}"

echo "=== 0. Strict clean Tier C (drop canned BEFORE strip) ==="
python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$TIER_C_IN" \
  --drop-canned \
  --strip-openers \
  --min-score "$MIN_SCORE" \
  --out "$TIER_C_CLEAN"

if [[ ! -f "$DISTILL" ]]; then
  echo "=== 1. Ollama distill (required for v4) ==="
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
  --out "$EG/training_data/ake_tier_d_long_v4.jsonl"

python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$EG/training_data/ake_tier_d_long_v4.jsonl" \
  --drop-canned --strip-openers --min-score "$MIN_SCORE" \
  --out "$EG/training_data/ake_tier_d_long_v4_clean.jsonl" --jsonl

echo "=== 3. Merge C + distill + D → v4 ==="
python3 "$API/scripts/build-tier-cde-merge.py" \
  --tier-c "$TIER_C_CLEAN" \
  --tier-d "$EG/training_data/ake_tier_d_long_v4_clean.jsonl" \
  --tier-e "$DISTILL" \
  --out "$CDE_BLEND" \
  --skip-needs-review \
  --min-assistant-score "$MIN_SCORE"

export TIER_C_LABEL_MASK=1
export TIER_C_BLENDED="$CDE_BLEND"

if [[ -d "$ADAPTER_DIR" ]] && [[ ! -d "$BACKUP_DIR" ]]; then
  echo "=== Backup adapter → $BACKUP_DIR ==="
  cp -a "$ADAPTER_DIR" "$BACKUP_DIR"
fi

echo "=== 4. Train (QLoRA) — log: $LOG ==="
systemctl stop unified-egregore 2>/dev/null || true
sleep 2
cd "$EG"
if pgrep -f "train_egregore_on_foundation_7b.py ake" >/dev/null 2>&1; then
  echo "Training already running"
else
  nohup "$VENV/bin/python" train_egregore_on_foundation_7b.py ake --qlora --epochs 2 >>"$LOG" 2>&1 &
  echo "Started PID $! — monitor: tail -f $LOG"
fi
