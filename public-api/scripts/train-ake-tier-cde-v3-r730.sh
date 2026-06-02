#!/usr/bin/env bash
# CDE retrain v3 — strict drop canned openers, min-score 0.4, cleaned D/E, QLoRA + label mask.
set -euo pipefail

EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
APPS_ROOT="${S2_APPS_ROOT:-/opt/s2-ecosystem}"
VENV="${VENV:-/opt/s2-ecosystem/venv-vllm-p40-src}"
LOG="${LOG:-/var/log/s2-ake-tier-cde-v3-train.log}"

TIER_C_IN="${TIER_C_IN:-$EG/training_data/ake_tier_c_blended.json}"
TIER_C_CLEAN="${TIER_C_CLEAN:-$EG/training_data/ake_tier_c_cleaned_v3.json}"
CDE_BLEND="${CDE_BLEND:-$EG/training_data/ake_tier_cde_blended_v3.json}"
ADAPTER_DIR="${OUTPUT_DIR:-/mnt/bipra/egregore-training/trained_models/ake}"
BACKUP_DIR="${ADAPTER_BACKUP:-/mnt/bipra/egregore-training/trained_models/ake_backup_pre_cde_v3}"
MIN_SCORE="${MIN_SCORE:-0.4}"

echo "=== 0. Strict clean Tier C (drop canned + strip survivors) ==="
python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$TIER_C_IN" \
  --drop-canned \
  --strip-openers \
  --min-score "$MIN_SCORE" \
  --out "$TIER_C_CLEAN"

echo "=== 1. Inventory ==="
python3 "$API/scripts/inventory-exploration-corpus.py" \
  --apps-root "$APPS_ROOT" \
  --out "$API/training_data/exploration_manifest.json"

echo "=== 2. Tier E ==="
python3 "$API/scripts/build-tier-e-exploration.py" \
  --apps-root "$APPS_ROOT" \
  --out "$EG/training_data/ake_tier_e_exploration.jsonl" \
  --review-out "$API/training_data/tier_e_human_review.md"

python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$EG/training_data/ake_tier_e_exploration.jsonl" \
  --drop-canned \
  --strip-openers \
  --min-score "$MIN_SCORE" \
  --out "$EG/training_data/ake_tier_e_exploration_clean.jsonl" \
  --jsonl

echo "=== 3. Tier D long (composed + expand from cleaned C) ==="
python3 "$API/scripts/build-tier-d-long-form-dataset.py" \
  --composed "$API/content/ake-field-message-composed.md" \
  --blended "$TIER_C_CLEAN" \
  --out "$EG/training_data/ake_tier_d_long_v3.jsonl"

python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$EG/training_data/ake_tier_d_long_v3.jsonl" \
  --drop-canned \
  --strip-openers \
  --min-score "$MIN_SCORE" \
  --out "$EG/training_data/ake_tier_d_long_v3_clean.jsonl" \
  --jsonl

echo "=== 4. Merge C+D+E → v3 blend ==="
python3 "$API/scripts/build-tier-cde-merge.py" \
  --tier-c "$TIER_C_CLEAN" \
  --tier-d "$EG/training_data/ake_tier_d_long_v3_clean.jsonl" \
  --tier-e "$EG/training_data/ake_tier_e_exploration_clean.jsonl" \
  --out "$CDE_BLEND" \
  --skip-needs-review \
  --min-assistant-score "$MIN_SCORE"

export TIER_C_LABEL_MASK=1
export TIER_C_BLENDED="$CDE_BLEND"

echo "=== 4b. Wire label-mask trainer ==="
"$VENV/bin/python" <<'PY'
from pathlib import Path

p = Path("/opt/s2-ecosystem/egregore-training/train_egregore_on_foundation_7b.py")
text = p.read_text(encoding="utf-8")
if "TIER_C_BLENDED" not in text:
    old = '        path = os.path.join(TRAINING_DATA_DIR, f"{egregore}_blended_dataset.json")'
    new = '''        tier_c = os.environ.get("TIER_C_BLENDED")
        path = tier_c if tier_c and os.path.exists(tier_c) else os.path.join(TRAINING_DATA_DIR, f"{egregore}_blended_dataset.json")'''
    if old in text:
        text = text.replace(old, new, 1)
if "TIER_C_LABEL_MASK" not in text:
    old_col = "    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)"
    new_col = '''    if os.environ.get("TIER_C_LABEL_MASK") == "1":
        sys.path.insert(0, "/opt/s2-ecosystem/egregore-training/scripts")
        from tier_c_label_mask_collator import TierCLabelMaskCollator
        data_collator = TierCLabelMaskCollator(
            tokenizer=tokenizer, response_prefix=f"{egregore.capitalize()}:"
        )
    else:
        data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)'''
    if old_col in text:
        text = text.replace(old_col, new_col, 1)
p.write_text(text, encoding="utf-8")
print("Trainer wired for TIER_C_BLENDED + TIER_C_LABEL_MASK")
PY

if [[ -d "$ADAPTER_DIR" ]] && [[ ! -d "$BACKUP_DIR" ]]; then
  echo "=== Backup adapter → $BACKUP_DIR ==="
  cp -a "$ADAPTER_DIR" "$BACKUP_DIR"
fi

echo "=== 5. Train (QLoRA) — log: $LOG ==="
systemctl stop unified-egregore 2>/dev/null || true
sleep 2
cd "$EG"
export TIER_C_BLENDED="$CDE_BLEND"
export TIER_C_LABEL_MASK=1
if pgrep -f "train_egregore_on_foundation_7b.py ake" >/dev/null 2>&1; then
  echo "Training already running"
else
  nohup "$VENV/bin/python" train_egregore_on_foundation_7b.py ake --qlora --epochs 2 >>"$LOG" 2>&1 &
  echo "Started PID $! — monitor: tail -f $LOG"
fi
