#!/usr/bin/env bash
# Production-safe unified :8100 on r730 — CPU, no CUDA OOM, hosted stays on Ollama.
# See docs/R730_UNIFIED_MEMORY_PLAN.md and docs/AKE_LORA_STATUS.md
set -euo pipefail

ADAPTERS_BASE="${ADAPTERS_BASE:-/mnt/bipra/egregore-training/trained_models}"
EG_DIR=/opt/s2-ecosystem/egregore-training
VENV="${VENV:-/opt/s2-ecosystem/venv/bin}"
DROPIN_DIR=/etc/systemd/system/unified-egregore.service.d

echo "=== Unified production-safe mode (CPU lab / eval) ==="

# Remove CUDA drop-ins (fp16 and 4-bit)
rm -f "$DROPIN_DIR/7b-cuda.conf" "$DROPIN_DIR/4bit-cuda.conf"

mkdir -p "$DROPIN_DIR"
cat > "$DROPIN_DIR/production-safe.conf" <<EOF
[Service]
Environment=EGREGORE_DEVICE=cpu
Environment=EGREGORE_USE_7B=1
Environment=ADAPTERS_BASE=$ADAPTERS_BASE
Environment=PORT=8100
Environment=EGREGORE_USE_PERSONA=0
Environment=EGREGORE_DO_SAMPLE=0
Environment=EGREGORE_DEFAULT_TEMPERATURE=0.2
Environment=EGREGORE_MAX_NEW_TOKENS=150
Environment=EGREGORE_ADAPTER_LOAD_MODE=egregore_only
EOF

# Keep tier-ab settings
cat > "$DROPIN_DIR/tier-ab.conf" <<EOF2
[Service]
Environment=EGREGORE_USE_PERSONA=0
Environment=EGREGORE_DO_SAMPLE=0
Environment=EGREGORE_DEFAULT_TEMPERATURE=0.2
Environment=EGREGORE_MAX_NEW_TOKENS=150
Environment=EGREGORE_ADAPTER_LOAD_MODE=egregore_only
EOF2

if [[ -f "$EG_DIR/unified_egregore_service/app.py" ]]; then
  systemctl stop unified-egregore-vllm-proxy.service 2>/dev/null || true
  systemctl daemon-reload
  systemctl restart unified-egregore.service
else
  echo "WARN: unified app not found at $EG_DIR — run setup-unified-8100-r730.sh first"
fi

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
  'UNIFIED_EGREGORE_TIMEOUT_MS=300000'; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s/^${key}=.*/${kv}/" "$ENV_FILE"
  else
    echo "$kv" >> "$ENV_FILE"
  fi
done

systemctl restart s2-public-api 2>/dev/null || true

echo "Waiting for :8100 (CPU load may take 30–90s)..."
for i in $(seq 1 30); do
  curl -sf "http://127.0.0.1:8100/health" >/dev/null 2>&1 && break
  sleep 3
done

curl -sf "http://127.0.0.1:8100/health" && echo || echo "health: not ready (CPU still loading)"
curl -sf "http://127.0.0.1:3020/health" 2>/dev/null | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print('hosted_inference:', d.get('hosted_inference'))" \
  || echo "gateway :3020 not up"

echo ""
echo "Hosted users: Ollama s2-ake (HOSTED_PREFER_UNIFIED_LORA=false)"
echo "After Tier C retrain: python3 scripts/tier-c-eval-gate-r730.py"
