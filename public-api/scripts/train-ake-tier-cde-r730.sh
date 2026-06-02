#!/usr/bin/env bash
# CDE retrain v2 — cleaned Tier C, fixed D/E generators, merged blend, QLoRA + label mask.
# Run on r730 after syncing public-api scripts.
set -euo pipefail

EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
APPS_ROOT="${S2_APPS_ROOT:-/opt/s2-ecosystem}"
VENV="${VENV:-/opt/s2-ecosystem/venv-vllm-p40-src}"
LOG="${LOG:-/var/log/s2-ake-tier-cde-v2-train.log}"

TIER_C_IN="${TIER_C_IN:-$EG/training_data/ake_tier_c_blended.json}"
TIER_C_CLEAN="${TIER_C_CLEAN:-$EG/training_data/ake_tier_c_cleaned.json}"
CDE_BLEND="${CDE_BLEND:-$EG/training_data/ake_tier_cde_blended_v2.json}"
ADAPTER_DIR="${OUTPUT_DIR:-/mnt/bipra/egregore-training/trained_models/ake}"
BACKUP_DIR="${ADAPTER_BACKUP:-/mnt/bipra/egregore-training/trained_models/ake_backup_pre_cde_v2}"

echo "=== 0. Clean Tier C (drop canned openers + strip) ==="
python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$TIER_C_IN" \
  --drop-canned \
  --strip-openers \
  --min-score 0.25 \
  --out "$TIER_C_CLEAN"

echo "=== 1. Inventory ==="
python3 "$API/scripts/inventory-exploration-corpus.py" \
  --apps-root "$APPS_ROOT" \
  --out "$API/training_data/exploration_manifest.json"

echo "=== 2. Tier E (rebuild — no canned openers in synthesizer) ==="
python3 "$API/scripts/build-tier-e-exploration.py" \
  --apps-root "$APPS_ROOT" \
  --out "$EG/training_data/ake_tier_e_exploration.jsonl" \
  --review-out "$API/training_data/tier_e_human_review.md"

echo "=== 3. Tier D long (rebuild from cleaned C) ==="
python3 "$API/scripts/build-tier-d-long-form-dataset.py" \
  --composed "$API/content/ake-field-message-composed.md" \
  --blended "$TIER_C_CLEAN" \
  --out "$EG/training_data/ake_tier_d_long.jsonl"

echo "=== 4. Merge C+D+E → v2 blend ==="
python3 "$API/scripts/build-tier-cde-merge.py" \
  --tier-c "$TIER_C_CLEAN" \
  --tier-d "$EG/training_data/ake_tier_d_long.jsonl" \
  --tier-e "$EG/training_data/ake_tier_e_exploration.jsonl" \
  --out "$CDE_BLEND" \
  --skip-needs-review \
  --min-assistant-score 0.25

echo "=== 4b. Wire label-mask trainer ==="
export TIER_C_LABEL_MASK=1
export TIER_C_BLENDED="$CDE_BLEND"
"$VENV/bin/python" <<'PY'
from pathlib import Path
import os

p = Path("/opt/s2-ecosystem/egregore-training/train_egregore_on_foundation_7b.py")
text = p.read_text(encoding="utf-8")

old_load = '        path = os.path.join(TRAINING_DATA_DIR, f"{egregore}_blended_dataset.json")'
new_load = '''        tier_c = os.environ.get("TIER_C_BLENDED")
        path = tier_c if tier_c and os.path.exists(tier_c) else os.path.join(TRAINING_DATA_DIR, f"{egregore}_blended_dataset.json")'''
if "TIER_C_BLENDED" not in text and old_load in text:
    text = text.replace(old_load, new_load, 1)
    print("Patched dataset path for TIER_C_BLENDED")

old_col = "    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)"
new_col = '''    if os.environ.get("TIER_C_LABEL_MASK") == "1":
        sys.path.insert(0, "/opt/s2-ecosystem/egregore-training/scripts")
        from tier_c_label_mask_collator import TierCLabelMaskCollator
        data_collator = TierCLabelMaskCollator(
            tokenizer=tokenizer, response_prefix=f"{egregore.capitalize()}:"
        )
    else:
        data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)'''
if "TIER_C_LABEL_MASK" not in text and old_col in text:
    text = text.replace(old_col, new_col, 1)
    print("Patched collator for TIER_C_LABEL_MASK")

old_tok = """    tokenized_dataset = dataset.map(
        tokenize_fn,
        batched=True,
        remove_columns=dataset.column_names,
    )"""
new_tok = """    if os.environ.get("TIER_C_LABEL_MASK") == "1":
        train_dataset = dataset
    else:
        tokenized_dataset = dataset.map(
            tokenize_fn,
            batched=True,
            remove_columns=dataset.column_names,
        )
        train_dataset = tokenized_dataset"""
if "train_dataset = dataset" not in text and old_tok in text:
    text = text.replace(old_tok, new_tok, 1)
    text = text.replace("train_dataset=tokenized_dataset,", "train_dataset=train_dataset,")
    print("Patched tokenize path for TIER_C_LABEL_MASK")

p.write_text(text, encoding="utf-8")
PY

if [[ -d "$ADAPTER_DIR" ]] && [[ ! -d "$BACKUP_DIR" ]]; then
  echo "=== Backup adapter → $BACKUP_DIR ==="
  cp -a "$ADAPTER_DIR" "$BACKUP_DIR"
fi

echo "=== 5. Train (QLoRA) — log: $LOG ==="
if pgrep -f "train_egregore_on_foundation_7b.py ake" >/dev/null 2>&1; then
  echo "Training already running — stop it or wait, then:"
  echo "  export TIER_C_BLENDED=$CDE_BLEND TIER_C_LABEL_MASK=1"
  echo "  nohup $VENV/bin/python $EG/train_egregore_on_foundation_7b.py ake --qlora --epochs 2 >>$LOG 2>&1 &"
else
  cd "$EG"
  nohup "$VENV/bin/python" train_egregore_on_foundation_7b.py ake --qlora --epochs 2 "$@" >>"$LOG" 2>&1 &
  echo "Started PID $! — monitor: tail -f $LOG"
fi

echo "=== 6. Post-train (run manually when train completes) ==="
echo "  systemctl restart unified-egregore"
echo "  bash $API/scripts/lab-lora-window-on-r730.sh"
echo "  python3 $API/scripts/tier-c-eval-gate-r730.py --lab-chat --skip-gateway"
