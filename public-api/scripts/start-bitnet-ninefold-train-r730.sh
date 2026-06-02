#!/usr/bin/env bash
# Background Ninefold BitNet LoRA train (GPU when P40 free) + deploy on completion.
# Stops Ollama/ComfyUI/sidecar for train; restores after.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
LOG="${LOG:-/var/log/s2-bitnet-ninefold-train.log}"
LOCK="${LOCK:-/var/run/s2-bitnet-ninefold-train.lock}"
BITNET_USE_GPU="${BITNET_USE_GPU:-auto}"

if [[ -f "$LOCK" ]] && kill -0 "$(cat "$LOCK")" 2>/dev/null; then
  echo "Ninefold BitNet train already running (PID $(cat "$LOCK"))"
  exit 0
fi

nohup env BITNET_USE_GPU="$BITNET_USE_GPU" bash -c "
  echo \"=== Ninefold BitNet train start \$(date -Iseconds) gpu=$BITNET_USE_GPU ===\" >>'$LOG'
  bash '$API/scripts/train-bitnet-ninefold-r730.sh' >>'$LOG' 2>&1
  bash '$API/scripts/deploy-bitnet-ninefold-r730.sh' >>'$LOG' 2>&1 || true
  systemctl restart s2-public-api 2>/dev/null || true
  echo \"=== Ninefold BitNet train done \$(date -Iseconds) ===\" >>'$LOG'
" >/dev/null 2>&1 &

echo $! >"$LOCK"
echo "Started Ninefold BitNet train PID $(cat "$LOCK") (BITNET_USE_GPU=$BITNET_USE_GPU) — tail -f $LOG"
