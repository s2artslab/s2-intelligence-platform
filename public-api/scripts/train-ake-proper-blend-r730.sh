#!/usr/bin/env bash
# Proper Ake blend: Tier F cross-egregore synthesis + CDE merge + QLoRA retrain.
# Run after current train_egregore_on_llama32.py finishes, or set FORCE=1 to queue next.
set -euo pipefail

EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
VENV="${VENV:-/opt/s2-ecosystem/venv-vllm-p40-src}"
LOG="${LOG:-/var/log/s2-ake-proper-blend-train.log}"
MIN_SCORE="${MIN_SCORE:-0.4}"
FORCE="${FORCE:-0}"

TIER_C_IN="${TIER_C_IN:-$EG/training_data/ake_tier_c_blended.json}"
TIER_C_CLEAN="${TIER_C_CLEAN:-$EG/training_data/ake_tier_c_cleaned_proper.json}"
TIER_F="${TIER_F:-$EG/training_data/ake_tier_f_egregore_synthesis.jsonl}"
DISTILL="${DISTILL:-$EG/training_data/ake_tier_c_ollama_distill.jsonl}"
CDE_BLEND="${CDE_BLEND:-$EG/training_data/ake_tier_cdef_blended_proper.json}"
ADAPTER_DIR="${OUTPUT_DIR:-/mnt/bipra/egregore-training/trained_models/ake-llama32}"
BACKUP_DIR="${ADAPTER_BACKUP:-/mnt/bipra/egregore-training/trained_models/ake-llama32_backup_pre_proper}"

if pgrep -f "train_egregore_on_llama32.py" >/dev/null 2>&1 && [[ "$FORCE" != "1" ]]; then
  echo "Llama32 QLoRA still running — re-run with FORCE=1 after it completes"
  exit 0
fi

PID_FILE="$EG/training_data/.ake-proper-blend-train.pid"
if [[ -f "$PID_FILE" ]]; then
  _old_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$_old_pid" ]] && kill -0 "$_old_pid" 2>/dev/null; then
    echo "Proper-blend train already running (PID $_old_pid) — exit"
    exit 0
  fi
fi

echo "=== 1. Tier F — cross-egregore synthesis blend ==="
python3 "$API/scripts/build-ake-egregore-synthesis-blend.py" \
  --training-dir "$EG/training_data" \
  --out "$TIER_F" \
  --per-egregore 400

echo "=== 2. Clean Tier C ==="
python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$TIER_C_IN" \
  --drop-canned --strip-openers --min-score "$MIN_SCORE" \
  --out "$TIER_C_CLEAN"

if [[ ! -f "$DISTILL" ]]; then
  echo "=== 3. Ollama distill (if missing) ==="
  systemctl start ollama 2>/dev/null || true
  sleep 2
  python3 "$API/scripts/build-tier-c-ollama-distill.py" \
    --prompts "$API/training_data/lora-distill-prompts.json" \
    --out "$DISTILL"
fi

echo "=== 4. Tier D from cleaned C ==="
python3 "$API/scripts/build-tier-d-long-form-dataset.py" \
  --composed "$API/content/ake-field-message-composed.md" \
  --blended "$TIER_C_CLEAN" \
  --out "$EG/training_data/ake_tier_d_long_proper.jsonl"

python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$EG/training_data/ake_tier_d_long_proper.jsonl" \
  --drop-canned --strip-openers --min-score "$MIN_SCORE" \
  --out "$EG/training_data/ake_tier_d_long_proper_clean.jsonl" --jsonl

echo "=== 5. Merge C + D + E + F (proper blend) ==="
python3 "$API/scripts/build-tier-cde-merge.py" \
  --tier-c "$TIER_C_CLEAN" \
  --tier-d "$EG/training_data/ake_tier_d_long_proper_clean.jsonl" \
  --tier-e "$DISTILL" \
  --tier-f "$TIER_F" \
  --out "$CDE_BLEND" \
  --skip-needs-review \
  --min-assistant-score "$MIN_SCORE"

cp "$API/scripts/train_egregore_on_llama32.py" "$EG/train_egregore_on_llama32.py"
cp "$API/scripts/tier-c-label-mask-collator.py" "$EG/scripts/tier_c_label_mask_collator.py"

export TIER_C_LABEL_MASK=1
export TIER_C_BLENDED="$CDE_BLEND"
export BASE_MODEL="${BASE_MODEL:-meta-llama/Llama-3.2-3B-Instruct}"
export OUTPUT_DIR="$ADAPTER_DIR"

if [[ -d "$ADAPTER_DIR" ]] && [[ ! -d "$BACKUP_DIR" ]]; then
  cp -a "$ADAPTER_DIR" "$BACKUP_DIR"
fi

echo "=== 6. Train Llama 3.2 QLoRA (proper blend) — log: $LOG ==="
# shellcheck source=r730-gpu-train-guard.sh
. "$API/scripts/r730-gpu-train-guard.sh"
r730_pause_comfyui_for_gpu_train
cd "$EG"
nohup "$VENV/bin/python" train_egregore_on_llama32.py ake --qlora --epochs 2 >>"$LOG" 2>&1 &
TRAIN_PID=$!
echo "$TRAIN_PID" >"$EG/training_data/.ake-proper-blend-train.pid"
echo "Started PID $TRAIN_PID — monitor: tail -f $LOG"
echo "After complete: bash $API/scripts/deploy-ake-lora-ollama-r730.sh"
