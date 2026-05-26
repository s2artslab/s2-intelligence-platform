#!/usr/bin/env bash
# QLoRA-style unified :8100 — 4-bit NF4 base on Tesla P40 (~6–8 GB VRAM + LoRA).
# Use after Tier C train completes and GPU has headroom. Keeps HOSTED_PREFER_UNIFIED_LORA=false.
# See docs/R730_UNIFIED_MEMORY_PLAN.md
set -euo pipefail

ADAPTERS_BASE="${ADAPTERS_BASE:-/mnt/bipra/egregore-training/trained_models}"
P40_VENV=/opt/s2-ecosystem/venv-vllm-p40-src
EG_DIR=/opt/s2-ecosystem/egregore-training
API_DIR=/opt/s2-ecosystem/public-api
DROPIN_DIR=/etc/systemd/system/unified-egregore.service.d
DROPIN="$DROPIN_DIR/4bit-cuda.conf"

echo "=== Unified 4-bit CUDA (QLoRA-style serve) ==="

if ! "$P40_VENV/bin/python" -c "import bitsandbytes" 2>/dev/null; then
  echo "Installing bitsandbytes in P40 venv..."
  "$P40_VENV/bin/pip" install -q bitsandbytes
fi
"$P40_VENV/bin/pip" install -q gunicorn flask

python3 "$API_DIR/scripts/apply-unified-4bit-inference-patch-r730.py" --eg-dir "$EG_DIR"

# Free VRAM: CPU drop-in and full-precision CUDA experiment must not override 4-bit
rm -f "$DROPIN_DIR/production-safe.conf" "$DROPIN_DIR/7b-cuda.conf" "$DROPIN_DIR/cpu.conf"

mkdir -p "$DROPIN_DIR"
cat > "$DROPIN" <<EOF
[Service]
Environment=EGREGORE_DEVICE=cuda
Environment=EGREGORE_LOAD_IN_4BIT=1
Environment=EGREGORE_USE_7B=1
Environment=ADAPTERS_BASE=$ADAPTERS_BASE
Environment=PORT=8100
Environment=EGREGORE_USE_PERSONA=0
Environment=EGREGORE_DO_SAMPLE=0
Environment=EGREGORE_DEFAULT_TEMPERATURE=0.2
Environment=EGREGORE_MAX_NEW_TOKENS=150
Environment=EGREGORE_ADAPTER_LOAD_MODE=egregore_only
ExecStart=
ExecStart=$P40_VENV/bin/gunicorn -w 1 -b 0.0.0.0:8100 --timeout 300 app:app
EOF

cat > "$DROPIN_DIR/tier-ab.conf" <<EOF2
[Service]
Environment=EGREGORE_USE_PERSONA=0
Environment=EGREGORE_DO_SAMPLE=0
Environment=EGREGORE_DEFAULT_TEMPERATURE=0.2
Environment=EGREGORE_MAX_NEW_TOKENS=150
Environment=EGREGORE_ADAPTER_LOAD_MODE=egregore_only
EOF2

systemctl stop unified-egregore-vllm-proxy.service 2>/dev/null || true
systemctl daemon-reload
systemctl restart unified-egregore.service

ENV_FILE=/opt/s2-ecosystem/public-api/.env
touch "$ENV_FILE"
if grep -q '^HOSTED_PREFER_UNIFIED_LORA=' "$ENV_FILE" 2>/dev/null; then
  sed -i 's/^HOSTED_PREFER_UNIFIED_LORA=.*/HOSTED_PREFER_UNIFIED_LORA=false/' "$ENV_FILE"
else
  echo 'HOSTED_PREFER_UNIFIED_LORA=false' >> "$ENV_FILE"
fi
for kv in \
  'UNIFIED_USE_PERSONA=0' \
  'UNIFIED_DO_SAMPLE=0' \
  'UNIFIED_MAX_TOKENS=150' \
  'UNIFIED_TEMPERATURE=0.2' \
  'UNIFIED_EGREGORE_TIMEOUT_MS=180000'; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s/^${key}=.*/${kv}/" "$ENV_FILE"
  else
    echo "$kv" >> "$ENV_FILE"
  fi
done
systemctl restart s2-public-api 2>/dev/null || true

echo "Waiting for :8100 (4-bit load ~30–60s)..."
for i in $(seq 1 25); do
  if curl -sf "http://127.0.0.1:8100/health" >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

echo "--- health ---"
curl -sf "http://127.0.0.1:8100/health" || echo "health: not ready — check journalctl -u unified-egregore"
echo ""
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null || true
echo ""
echo "Lab: https://api.s2artslab.com/lab/ake-unified-lora"
echo "Next: python3 $API_DIR/scripts/tier-c-eval-gate-r730.py"
