#!/usr/bin/env bash
# Tier C Ake 7B retrain on r730 (foundation stack + label-mask collator).
set -euo pipefail

EG=/opt/s2-ecosystem/egregore-training
VENV="${VENV:-/opt/s2-ecosystem/venv-vllm-p40-src}"
LOG="${LOG:-/var/log/s2-ake-tier-c-train.log}"
TRAIN="$EG/train_egregore_on_foundation_7b.py"

cd "$EG"
"$VENV/bin/python" /opt/s2-ecosystem/public-api/scripts/build-tier-c-v2-from-blended.py

export TIER_C_LABEL_MASK=1
export TIER_C_BLENDED="$EG/training_data/ake_tier_c_blended.json"

"$VENV/bin/python" <<'PY'
from pathlib import Path
import os

p = Path("/opt/s2-ecosystem/egregore-training/train_egregore_on_foundation_7b.py")
text = p.read_text(encoding="utf-8")

old_load = '        path = os.path.join(TRAINING_DATA_DIR, f"{egregore}_blended_dataset.json")'
new_load = '''        tier_c = os.environ.get("TIER_C_BLENDED")
        path = tier_c if tier_c and os.path.exists(tier_c) else os.path.join(TRAINING_DATA_DIR, f"{egregore}_blended_dataset.json")'''
if old_load in text and "TIER_C_BLENDED" not in text:
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
if old_col in text and "TIER_C_LABEL_MASK" not in text:
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
if old_tok in text and "train_dataset = dataset" not in text:
    text = text.replace(old_tok, new_tok, 1)
    text = text.replace("train_dataset=tokenized_dataset,", "train_dataset=train_dataset,")
    print("Patched tokenize path for TIER_C_LABEL_MASK")

p.write_text(text, encoding="utf-8")
PY

if pgrep -f "train_egregore_on_foundation_7b.py ake" >/dev/null 2>&1; then
  echo "Training already running — skip start. tail -f $LOG"
  exit 0
fi

echo "Starting Tier C training (log: $LOG) ..."
nohup "$VENV/bin/python" "$TRAIN" ake --qlora --epochs 2 >>"$LOG" 2>&1 &
echo "PID $! — monitor: tail -f $LOG"
