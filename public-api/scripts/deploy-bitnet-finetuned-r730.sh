#!/usr/bin/env bash
# Deploy fine-tuned BitNet LoRA adapter to sidecar + restart gateway.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
ADAPTER="${BITNET_LORA_ADAPTER:-$EG/training_data/bitnet_ake_lora.gguf}"
UNIT=/etc/systemd/system/bitnet-sidecar.service

if [[ ! -f "$ADAPTER" ]]; then
  echo "ERROR: LoRA adapter not found: $ADAPTER"
  echo "Run train-bitnet-lora-r730.sh first"
  exit 1
fi

echo "=== Deploy BitNet LoRA adapter ==="
echo "Adapter: $ADAPTER"

if [[ -f "$UNIT" ]]; then
  mkdir -p /etc/systemd/system/bitnet-sidecar.service.d
  cat > /etc/systemd/system/bitnet-sidecar.service.d/lora.conf <<EOF
[Service]
Environment=BITNET_LORA_ADAPTER_PATH=$ADAPTER
Environment=BITNET_MODEL=bitnet-b1.58-2B-4T-ake-lora
Environment=BITNET_QVAC_MODEL_PATH=${BITNET_QVAC_MODEL_PATH:-/opt/qvac-fabric-llm.cpp/models/BitNet-b1.58-2B-4T-tq2/dl-gianni-cor/bitnet_b1_58-xl-TQ2_0/bitnet_b1_58-xl-TQ2_0.gguf}
Environment=BITNET_QVAC_CLI=${BITNET_QVAC_CLI:-/opt/qvac-fabric-llm.cpp/build/bin/llama-cli}
Environment=BITNET_QVAC_NGL=${BITNET_QVAC_NGL:-999}
Environment=BITNET_INFERENCE_TIMEOUT=180
EOF
  systemctl daemon-reload
  systemctl restart bitnet-sidecar.service
else
  echo "WARN: $UNIT missing — run setup-bitnet-sidecar-r730.sh"
fi

ENV_FILE="${ENV_FILE:-/opt/s2-ecosystem/public-api/.env}"
touch "$ENV_FILE"
if grep -q '^BITNET_ENABLED=' "$ENV_FILE"; then
  sed -i 's/^BITNET_ENABLED=.*/BITNET_ENABLED=true/' "$ENV_FILE"
else
  echo 'BITNET_ENABLED=true' >> "$ENV_FILE"
fi

systemctl restart s2-public-api 2>/dev/null || systemctl restart s2-intelligence-public-api 2>/dev/null || true
sleep 2

echo "=== Sidecar health ==="
curl -sf http://127.0.0.1:8120/health | python3 -m json.tool || true

echo "=== Benchmark ==="
python3 "$API/scripts/bitnet-benchmark-r730.py" --gateway http://127.0.0.1:3020 || true

echo "Done."
