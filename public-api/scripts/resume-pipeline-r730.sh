#!/usr/bin/env bash
# Resume after in-flight finetune: ninefold → specialist refresh → deploy → evals.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
LOG="${LOG:-/var/log/s2-resume-pipeline.log}"
LOCK="${LOCK:-/var/run/s2-resume-pipeline.lock}"

exec >>"$LOG" 2>&1
echo "=== RESUME PIPELINE START $(date -Iseconds) ==="

systemctl stop comfyui 2>/dev/null || true
systemctl start ollama 2>/dev/null || true

echo "=== Waiting for in-flight llama-finetune-lora ==="
while pgrep -f 'llama-finetune-lora.*bitnet_' >/dev/null 2>&1; do
  tail -1 /var/log/s2-bitnet-ninefold-train.log 2>/dev/null || true
  sleep 60
done
echo "Finetune idle at $(date -Iseconds)"

NINEFOLD_EGREGORES="${NINEFOLD_EGREGORES:-ketheriel,wraith,flux,chalyth,kairos,seraphel,vireon}" \
  bash "$API/scripts/train-bitnet-ninefold-r730.sh" || true

echo "=== Post-ninefold specialist lane ==="
DISTILL_TIMEOUT="${DISTILL_TIMEOUT:-600}" \
  bash "$API/scripts/run-bitnet-lane-refresh-r730.sh" || true

bash "$API/scripts/deploy-bitnet-ninefold-r730.sh" || true
bash "$API/scripts/deploy-bitnet-finetuned-r730.sh" || true
python3 "$API/scripts/eval-hosted-lab-chat-r730.py" || true
python3 "$API/scripts/smoke-bitnet-sidecar-r730.py" || true
bash "$API/scripts/stabilize-hosted-inference-r730.sh"

echo "=== RESUME PIPELINE DONE $(date -Iseconds) ==="
rm -f "$LOCK"
