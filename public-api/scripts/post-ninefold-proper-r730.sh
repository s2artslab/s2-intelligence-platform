#!/usr/bin/env bash
# After current Llama32 train: proper Ake blend retrain + Ninefold BitNet egregores.
#
#   nohup bash /opt/s2-ecosystem/public-api/scripts/post-ninefold-proper-r730.sh \
#     >>/var/log/s2-ninefold-proper-pipeline.log 2>&1 &
#
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
LOG="${LOG:-/var/log/s2-ninefold-proper-pipeline.log}"
POLL="${POLL_SEC:-120}"

log() { echo "[$(date -Iseconds)] $*"; }

log "Ninefold proper pipeline — waiting for in-flight Llama32 train..."

while pgrep -f "train_egregore_on_llama32.py" >/dev/null 2>&1; do
  log "Llama32 train running — sleep ${POLL}s"
  sleep "$POLL"
done

log "Phase 1: Ake proper blend (Tier F cross-egregore synthesis)"
FORCE=1 bash "$API/scripts/train-ake-proper-blend-r730.sh"

PID_FILE="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}/training_data/.ake-proper-blend-train.pid"
while true; do
  if pgrep -f "train_egregore_on_llama32.py" >/dev/null 2>&1; then
    log "Proper-blend train running — sleep ${POLL}s"
    sleep "$POLL"
    continue
  fi
  if [[ -f "$PID_FILE" ]]; then
    blend_pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [[ -n "$blend_pid" ]] && kill -0 "$blend_pid" 2>/dev/null; then
      log "Proper-blend train PID $blend_pid — sleep ${POLL}s"
      sleep "$POLL"
      continue
    fi
  fi
  break
done
rm -f "$PID_FILE" 2>/dev/null || true

TRAIN_LOG="${TRAIN_LOG:-/var/log/s2-ake-proper-blend-train.log}"
# shellcheck source=r730-gpu-train-guard.sh
. "$API/scripts/r730-gpu-train-guard.sh"
if ! r730_qlora_train_complete_in_log "$TRAIN_LOG"; then
  log "WARN proper-blend QLoRA did not finish (no epoch 2.0 in $TRAIN_LOG) — skipping deploy/BitNet"
  log "Re-run: FORCE=1 bash $API/scripts/train-ake-proper-blend-r730.sh"
  exit 1
fi
r730_resume_comfyui_after_gpu_train

log "Phase 2: Deploy Ake Llama32 LoRA"
bash "$API/scripts/prep-deploy-ake-lora-r730.sh" || log "WARN prep deploy"
OLLAMA_PREFER_LORA="${OLLAMA_PREFER_LORA:-false}" bash "$API/scripts/deploy-ake-lora-ollama-r730.sh" || true
python3 "$API/scripts/eval-ake-llama32-lora-r730.py" || log "WARN Ake eval failed — review logs"

log "Phase 3: Ninefold BitNet egregores (8 × 1.58-bit LoRA)"
if bash "$API/scripts/train-bitnet-ninefold-r730.sh"; then
  bash "$API/scripts/deploy-bitnet-ninefold-r730.sh" || true
else
  log "WARN BitNet ninefold train failed — check /var/log/s2-qvac-build.log and s2-bitnet-ninefold-train.log"
fi

log "Ninefold proper pipeline complete."
