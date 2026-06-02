#!/usr/bin/env bash
# Setup BitNet b1.58 experimental sidecar on r730 (CPU, port 8120).
# Idempotent — safe to re-run.
#
#   bash scripts/setup-bitnet-sidecar-r730.sh
#   BITNET_STUB=1 bash scripts/setup-bitnet-sidecar-r730.sh   # stub only (no model download)
set -euo pipefail

ROOT="${ROOT:-/opt/s2-ecosystem/public-api}"
BITNET_ROOT="${BITNET_ROOT:-/opt/bitnet.cpp}"
MODEL_DIR="${BITNET_ROOT}/models/BitNet-b1.58-2B-4T"
SIDECAR_PORT="${BITNET_SIDECAR_PORT:-8120}"
STUB="${BITNET_STUB:-0}"

echo "== BitNet 1.58-bit experimental lane setup =="
echo "  public-api: $ROOT"
echo "  bitnet.cpp: $BITNET_ROOT"
echo "  sidecar:    127.0.0.1:$SIDECAR_PORT"

mkdir -p "$BITNET_ROOT/models"

if [[ ! -d "$BITNET_ROOT/.git" ]]; then
  echo "Cloning microsoft/BitNet → $BITNET_ROOT"
  git clone --depth 1 https://github.com/microsoft/BitNet.git "$BITNET_ROOT"
else
  echo "BitNet repo present — git pull"
  git -C "$BITNET_ROOT" pull --ff-only || true
fi

if [[ "$STUB" != "1" ]]; then
  if command -v hf >/dev/null 2>&1; then
    HF_CLI=hf
  elif command -v huggingface-cli >/dev/null 2>&1; then
    HF_CLI=huggingface-cli
  else
    echo "WARN: hf CLI not found — sidecar will run in stub mode until model is present"
    STUB=1
  fi

  if [[ "$STUB" != "1" ]]; then
    echo "Downloading BitNet b1.58 2B4T GGUF weights..."
    "$HF_CLI" download microsoft/bitnet-b1.58-2B-4T-gguf \
      --local-dir "$MODEL_DIR" \
      --include "*.gguf" || {
        echo "WARN: model download failed — stub mode"
        STUB=1
      }
  fi
fi

# systemd unit for sidecar
UNIT=/etc/systemd/system/bitnet-sidecar.service
cat > "$UNIT" <<EOF
[Unit]
Description=S2 BitNet b1.58 sidecar (experimental)
After=network.target

[Service]
Type=simple
WorkingDirectory=$ROOT
Environment=BITNET_ROOT=$BITNET_ROOT
Environment=BITNET_MODEL_PATH=$MODEL_DIR/ggml-model-i2_s.gguf
Environment=BITNET_SIDECAR_PORT=$SIDECAR_PORT
Environment=BITNET_STUB=$STUB
ExecStart=/usr/bin/python3 $ROOT/scripts/bitnet-sidecar-server.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable bitnet-sidecar.service
systemctl restart bitnet-sidecar.service

echo "Sidecar status:"
curl -sf "http://127.0.0.1:$SIDECAR_PORT/health" | python3 -m json.tool || echo "WARN: sidecar health check failed"

# Patch gateway env if public-api .env exists
ENV_FILE="${ENV_FILE:-/opt/s2-ecosystem/public-api/.env}"
if [[ -f "$ENV_FILE" ]]; then
  grep -q '^BITNET_ENABLED=' "$ENV_FILE" || echo "BITNET_ENABLED=true" >> "$ENV_FILE"
  grep -q '^BITNET_BASE_URL=' "$ENV_FILE" || echo "BITNET_BASE_URL=http://127.0.0.1:$SIDECAR_PORT" >> "$ENV_FILE"
  grep -q '^BITNET_MODEL=' "$ENV_FILE" || echo "BITNET_MODEL=bitnet-b1.58-2B-4T" >> "$ENV_FILE"
  echo "Gateway env patched ($ENV_FILE) — restart public-api to pick up BITNET_* vars"
fi

echo "Done. Next:"
echo "  1. Restart gateway: systemctl restart s2-public-api  (or your unit name)"
echo "  2. Run benchmark: python3 $ROOT/scripts/bitnet-benchmark-r730.py"
echo "  3. Research API: curl http://127.0.0.1:3020/api/research/bitnet/status"
