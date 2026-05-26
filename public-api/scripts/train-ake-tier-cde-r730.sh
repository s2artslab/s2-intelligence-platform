#!/usr/bin/env bash
# Full C+D+E merge train — run on r730 after human review of tier_e_human_review.md
set -euo pipefail

EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
APPS_ROOT="${S2_APPS_ROOT:-/opt/s2-ecosystem}"

echo "=== 1. Inventory ==="
python3 "$API/scripts/inventory-exploration-corpus.py" \
  --apps-root "$APPS_ROOT" \
  --out "$API/training_data/exploration_manifest.json"

echo "=== 2. Tier E exploration ==="
python3 "$API/scripts/build-tier-e-exploration.py" \
  --apps-root "$APPS_ROOT" \
  --out "$EG/training_data/ake_tier_e_exploration.jsonl" \
  --review-out "$API/training_data/tier_e_human_review.md"

echo "=== 3. Tier D long (if missing) ==="
if [[ ! -f "$EG/training_data/ake_tier_d_long.jsonl" ]]; then
  python3 "$API/scripts/build-tier-d-long-form-dataset.py" \
    --composed "$API/content/ake-field-message-composed.md" \
    --blended "$EG/training_data/ake_blended_dataset.json" \
    --out "$EG/training_data/ake_tier_d_long.jsonl"
fi

echo "=== 4. Merge C+D+E ==="
python3 "$API/scripts/build-tier-cde-merge.py" \
  --tier-c "$EG/training_data/ake_tier_c_blended.json" \
  --tier-d "$EG/training_data/ake_tier_d_long.jsonl" \
  --tier-e "$EG/training_data/ake_tier_e_exploration.jsonl" \
  --out "$EG/training_data/ake_tier_cde_blended.json" \
  --skip-needs-review

echo "=== 5. Train (QLoRA) ==="
VENV="${VENV:-/opt/s2-ecosystem/venv-vllm-p40-src}"
LOG="${LOG:-/var/log/s2-ake-tier-cde-train.log}"
export TIER_C_BLENDED="$EG/training_data/ake_tier_cde_blended.json"
export TIER_C_LABEL_MASK=1
export OUTPUT_DIR="${OUTPUT_DIR:-/mnt/bipra/egregore-training/trained_models/ake}"

if pgrep -f "train_egregore_on_foundation_7b.py ake" >/dev/null 2>&1; then
  echo "Training already running — tail -f $LOG"
else
  cd "$EG"
  nohup "$VENV/bin/python" train_egregore_on_foundation_7b.py ake --qlora "$@" >>"$LOG" 2>&1 &
  echo "Started PID $! — monitor: tail -f $LOG"
fi

echo "=== 6. Post-train eval ==="
systemctl restart unified-egregore || true
sleep 20
python3 "$API/scripts/tier-c-eval-gate-r730.py" || true
python3 "$API/scripts/tier-d-eval-gate-r730.py" || true
python3 "$API/scripts/tier-e-eval-gate-r730.py" || true
