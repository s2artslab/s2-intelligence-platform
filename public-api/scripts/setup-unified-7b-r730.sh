#!/usr/bin/env bash
# 7B stacked Ake (foundation + egregore) on :8100 — Tesla P40 venv, CUDA.
# WARNING: Often OOM on P40. Keeps HOSTED_PREFER_UNIFIED_LORA=false.
# Production safe mode: scripts/setup-unified-production-r730.sh
# See docs/R730_UNIFIED_MEMORY_PLAN.md
set -euo pipefail

ADAPTERS_BASE="${ADAPTERS_BASE:-/mnt/bipra/egregore-training/trained_models}"
P40_VENV=/opt/s2-ecosystem/venv-vllm-p40-src
EG_DIR=/opt/s2-ecosystem/egregore-training
DROPIN=/etc/systemd/system/unified-egregore.service.d/7b-cuda.conf

"$P40_VENV/bin/pip" install -q gunicorn flask

mkdir -p /etc/systemd/system/unified-egregore.service.d
cat > "$DROPIN" <<EOF
[Service]
Environment=EGREGORE_DEVICE=cuda
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

TIER_AB=/etc/systemd/system/unified-egregore.service.d/tier-ab.conf
cat > "$TIER_AB" <<EOF2
[Service]
Environment=EGREGORE_USE_PERSONA=0
Environment=EGREGORE_DO_SAMPLE=0
Environment=EGREGORE_DEFAULT_TEMPERATURE=0.2
Environment=EGREGORE_MAX_NEW_TOKENS=150
Environment=EGREGORE_ADAPTER_LOAD_MODE=egregore_only
EOF2

rm -f /etc/systemd/system/unified-egregore.service.d/cpu.conf
rm -f /etc/systemd/system/unified-egregore.service.d/production-safe.conf
rm -f /etc/systemd/system/unified-egregore.service.d/4bit-cuda.conf
systemctl stop unified-egregore-vllm-proxy.service 2>/dev/null || true
systemctl daemon-reload
systemctl restart unified-egregore.service

ENV_FILE=/opt/s2-ecosystem/public-api/.env
if grep -q '^HOSTED_PREFER_UNIFIED_LORA=' "$ENV_FILE" 2>/dev/null; then
  sed -i 's/^HOSTED_PREFER_UNIFIED_LORA=.*/HOSTED_PREFER_UNIFIED_LORA=false/' "$ENV_FILE"
else
  echo 'HOSTED_PREFER_UNIFIED_LORA=false' >> "$ENV_FILE"
fi
for kv in \
  'UNIFIED_USE_PERSONA=0' \
  'UNIFIED_DO_SAMPLE=0' \
  'UNIFIED_MAX_TOKENS=150' \
  'UNIFIED_TEMPERATURE=0.2'; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s/^${key}=.*/${kv}/" "$ENV_FILE"
  else
    echo "$kv" >> "$ENV_FILE"
  fi
done
systemctl restart s2-public-api

echo "Waiting for :8100..."
for i in $(seq 1 15); do
  curl -sf "http://127.0.0.1:8100/health" >/dev/null 2>&1 && break
  sleep 3
done
curl -sf "http://127.0.0.1:8100/health" && echo
curl -sf "http://127.0.0.1:3020/health" | python3 -c "import sys,json; d=json.load(sys.stdin); print('hosted_inference:', d.get('hosted_inference'))"
