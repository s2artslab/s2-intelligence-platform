#!/usr/bin/env bash
# Start background post-train deploy+eval watcher (safe while GPU train runs).
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
LOG="/var/log/s2-ake-llama32-post-train.log"

if pgrep -f "bash $API/scripts/post-train-ake-lora-r730.sh" >/dev/null 2>&1; then
  echo "Watcher already running"
  pgrep -af "post-train-ake-lora-r730.sh" | grep -v pgrep || true
  exit 0
fi

nohup bash "$API/scripts/post-train-ake-lora-r730.sh" >>"$LOG" 2>&1 &
echo "Started post-train watcher PID $! — log: $LOG"
