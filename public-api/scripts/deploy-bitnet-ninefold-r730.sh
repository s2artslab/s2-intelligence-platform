#!/usr/bin/env bash
# Deploy Ninefold BitNet egregore LoRA registry to sidecar.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
REGISTRY="${BITNET_EGREGORE_REGISTRY:-$EG/training_data/bitnet_adapters/bitnet_egregore_registry.json}"
UNIT=/etc/systemd/system/bitnet-sidecar.service

if [[ ! -f "$REGISTRY" ]]; then
  echo "ERROR: Registry not found: $REGISTRY"
  echo "Run train-bitnet-ninefold-r730.sh first"
  exit 1
fi

echo "=== Deploy Ninefold BitNet registry ==="
cat "$REGISTRY" | python3 -m json.tool

mkdir -p /etc/systemd/system/bitnet-sidecar.service.d
cat > /etc/systemd/system/bitnet-sidecar.service.d/ninefold.conf <<EOF
[Service]
Environment=BITNET_EGREGORE_REGISTRY=$REGISTRY
Environment=BITNET_MODEL=bitnet-b1.58-2B-4T-ninefold
EOF

if [[ -f "$UNIT" ]]; then
  systemctl daemon-reload
  systemctl restart bitnet-sidecar.service
else
  bash "$API/scripts/setup-bitnet-sidecar-r730.sh"
fi

ENV_FILE="${ENV_FILE:-/opt/s2-ecosystem/public-api/.env}"
touch "$ENV_FILE"
grep -q '^BITNET_ENABLED=' "$ENV_FILE" && sed -i 's/^BITNET_ENABLED=.*/BITNET_ENABLED=true/' "$ENV_FILE" || echo 'BITNET_ENABLED=true' >>"$ENV_FILE"

systemctl restart s2-public-api 2>/dev/null || true
sleep 2
curl -sf http://127.0.0.1:8120/health | python3 -m json.tool || true
echo "Done."
