#!/usr/bin/env bash
set -euo pipefail
echo "=== SERVICES ==="
for s in ollama comfyui s2-public-api bitnet-sidecar egregorelab-gateway unified-egregore; do
  printf "%-22s %s\n" "$s:" "$(systemctl is-active "$s" 2>/dev/null || echo n/a)"
done
echo "=== OLLAMA ==="
ollama list 2>/dev/null || true
echo "=== ENV ==="
grep -E '^(OLLAMA_|EGREGORE_|BITNET_)' /opt/s2-ecosystem/public-api/.env 2>/dev/null | head -15 || true
echo "=== MOUNTS ==="
mount | grep -E 'bipra|s2-data' || true
echo "=== LLAMA ADAPTER ==="
ls -la /mnt/bipra/egregore-training/trained_models/ake-llama32/ 2>/dev/null | head -8 || echo "path missing"
echo "=== BITNET TRAIN ==="
pgrep -af 'llama-finetune-lora|train-bitnet-ninefold' | head -3 || echo "none"
tail -1 /var/log/s2-bitnet-ninefold-train.log 2>/dev/null | tr '\r' '\n' | tail -1 || true
