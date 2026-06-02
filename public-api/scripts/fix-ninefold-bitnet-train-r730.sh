#!/usr/bin/env bash
# Stop bad ninefold finetune, rebuild filtered datasets, retrain from scratch.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
DATA_DIR="${BITNET_EGREGORE_DATA:-$EG/training_data/bitnet_egregores}"
ADAPTER_DIR="${BITNET_ADAPTER_DIR:-$EG/training_data/bitnet_adapters}"
LOG="${LOG:-/var/log/s2-fix-ninefold-bitnet.log}"

exec > >(tee -a "$LOG") 2>&1
echo "=== fix-ninefold-bitnet $(date -Iseconds) ==="

bash "$API/scripts/setup-r730-gpu-lane-policy-r730.sh" hosted

echo "=== Stop in-flight finetune / resume ==="
pkill -f 'llama-finetune-lora.*bitnet_' 2>/dev/null || true
pkill -f resume-pipeline-r730.sh 2>/dev/null || true
sleep 3

echo "=== Audit current datasets ==="
for f in "$DATA_DIR"/bitnet_*.jsonl; do
  [[ -f "$f" ]] || continue
  python3 "$API/scripts/audit-ake-assistant-quality.py" \
    --input "$f" \
    --jsonl \
    --sample-bad 3 || true
done

echo "=== Rebuild filtered datasets (min-score 0.5) ==="
python3 "$API/scripts/build-bitnet-egregore-dataset.py" \
  --training-dir "$EG/training_data" \
  --out-dir "$DATA_DIR" \
  --per-egregore 800 \
  --min-score 0.5

echo "=== Remove partial / stale adapters (keep rhys if you want A/B) ==="
rm -f "$ADAPTER_DIR/bitnet_ketheriel_lora.gguf"
rm -rf /root/checkpoints ./checkpoints 2>/dev/null || true

echo "=== Retrain ninefold (CPU on P40; rhys skipped if exists) ==="
NINEFOLD_EGREGORES="${NINEFOLD_EGREGORES:-ketheriel,wraith,flux,chalyth,kairos,seraphel,vireon}" \
  FORCE_RETRAIN="${FORCE_RETRAIN:-1}" \
  BITNET_USE_GPU=false \
  bash "$API/scripts/train-bitnet-ninefold-r730.sh"

bash "$API/scripts/deploy-bitnet-ninefold-r730.sh" || true
python3 "$API/scripts/smoke-bitnet-sidecar-r730.py" || true

echo "=== Done ==="
