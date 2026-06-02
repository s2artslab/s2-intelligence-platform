#!/usr/bin/env bash
# Specialist refresh → remaining ninefold BitNet → deploy → evals.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
LOG="${LOG:-/var/log/s2-full-pipeline.log}"
LOCK="${LOCK:-/var/run/s2-full-pipeline.lock}"

exec >>"$LOG" 2>&1
echo "=== FULL PIPELINE START $(date -Iseconds) ==="

bash "$API/scripts/run-bitnet-lane-refresh-r730.sh"

NINEFOLD_EGREGORES="${NINEFOLD_EGREGORES:-ketheriel,wraith,flux,chalyth,kairos,seraphel,vireon}" \
  bash "$API/scripts/train-bitnet-ninefold-r730.sh"

# Specialist distill needs GPU free from finetune — retry refresh train/deploy only
echo "=== Post-ninefold specialist lane (distill + train + deploy) ==="
bash "$API/scripts/run-bitnet-lane-refresh-r730.sh" || true

bash "$API/scripts/deploy-bitnet-ninefold-r730.sh" || true
python3 "$API/scripts/eval-hosted-lab-chat-r730.py" || true
python3 "$API/scripts/smoke-bitnet-sidecar-r730.py" || true
bash "$API/scripts/stabilize-hosted-inference-r730.sh"

echo "=== FULL PIPELINE DONE $(date -Iseconds) ==="
rm -f "$LOCK"
