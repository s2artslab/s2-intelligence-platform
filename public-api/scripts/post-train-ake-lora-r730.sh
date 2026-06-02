#!/usr/bin/env bash
# Wait for Llama 3.2 QLoRA train to finish, deploy s2-ake-lora, run eval gate.
#
#   nohup bash /opt/s2-ecosystem/public-api/scripts/post-train-ake-lora-r730.sh >>/var/log/s2-ake-llama32-post-train.log 2>&1 &
#
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
ADAPTER="${LORA_ADAPTER_PATH:-/mnt/bipra/egregore-training/trained_models/ake-llama32/adapter_config.json}"
LOG="${LOG:-/var/log/s2-ake-llama32-post-train.log}"
POLL="${POLL_SEC:-120}"
PREFER_LORA="${OLLAMA_PREFER_LORA:-false}"

log() { echo "[$(date -Iseconds)] $*"; }

log "Post-train pipeline watching for completion..."

while pgrep -f "train_egregore_on_llama32.py" >/dev/null 2>&1; do
  log "Training still running — sleep ${POLL}s"
  sleep "$POLL"
done

log "Train process ended — waiting for adapter..."
for _ in $(seq 1 60); do
  if [[ -f "$ADAPTER" ]]; then
    break
  fi
  sleep 30
done

if [[ ! -f "$ADAPTER" ]]; then
  log "ERROR: adapter not found at $ADAPTER after 30m"
  exit 1
fi

log "Adapter ready — prep deploy"
bash "$API/scripts/prep-deploy-ake-lora-r730.sh" || log "WARN prep had failures — continuing deploy"

log "Deploy Ollama s2-ake-lora (PREFER_LORA=$PREFER_LORA)"
OLLAMA_PREFER_LORA="$PREFER_LORA" bash "$API/scripts/deploy-ake-lora-ollama-r730.sh"

log "Running eval gate..."
if python3 "$API/scripts/eval-ake-llama32-lora-r730.py"; then
  log "Eval PASS"
  if [[ "$PREFER_LORA" != "true" ]]; then
    log "To prefer LoRA in production: OLLAMA_PREFER_LORA=true bash $API/scripts/deploy-ake-lora-ollama-r730.sh"
  fi
else
  log "Eval FAIL — keep OLLAMA_PREFER_LORA=false; review /var/log/s2-ake-llama32-qlora-train.log"
  exit 1
fi

log "Post-train pipeline complete."
