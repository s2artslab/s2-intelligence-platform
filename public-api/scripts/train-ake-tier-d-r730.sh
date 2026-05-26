#!/usr/bin/env bash
# Tier D only (508 rows) — prefer train-ake-tier-cde-r730.sh for production retrain.
set -euo pipefail
echo "WARNING: Use train-ake-tier-cde-r730.sh for merged C+D+E. Continuing Tier D-only in 5s..."
sleep 5

EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"

echo "Building Tier D long-form dataset..."
python3 "$API/scripts/build-tier-d-long-form-dataset.py" \
  --composed "$API/content/ake-field-message-composed.md" \
  --blended "$EG/training_data/ake_blended_dataset.json" \
  --out "$EG/training_data/ake_tier_d_long.jsonl"

export TIER_C_BLENDED="$EG/training_data/ake_tier_d_long.jsonl"
export TIER_C_LABEL_MASK=1
export OUTPUT_DIR="${OUTPUT_DIR:-/mnt/bipra/egregore-training/trained_models/ake}"

cd "$EG"
echo "Training ake Tier D (long-form JSONL)..."
python3 train_egregore_on_foundation_7b.py ake --qlora "$@"

echo "Restart unified-egregore and run: python3 $API/scripts/tier-d-eval-gate-r730.py"
