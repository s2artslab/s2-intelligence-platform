#!/usr/bin/env bash
# Expose trained GPT-2 LoRAs on :8100 (Flask unified service — matches BIPRA weights).
set -euo pipefail

ADAPTERS_BASE="${ADAPTERS_BASE:-/mnt/bipra/egregore-training/trained_models}"
UNIT=/etc/systemd/system/unified-egregore.service
EG_DIR=/opt/s2-ecosystem/egregore-training
VENV=/opt/s2-ecosystem/venv/bin

cat > "$UNIT" <<EOF
[Unit]
Description=Unified Egregore Service (trained LoRA adapters)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$EG_DIR/unified_egregore_service
Environment=ADAPTERS_BASE=$ADAPTERS_BASE
Environment=EGREGORE_USE_7B=0
Environment=PORT=8100
Environment=EGREGORE_DEVICE=cpu
ExecStart=$VENV/gunicorn -w 1 -b 0.0.0.0:8100 --timeout 300 app:app
Restart=on-failure
RestartSec=15

[Install]
WantedBy=multi-user.target
EOF

# Stop vLLM proxy on 8111 if it would conflict; keep vLLM on 8110 for experiments
systemctl stop unified-egregore-vllm-proxy.service 2>/dev/null || true
systemctl disable unified-egregore-vllm-proxy.service 2>/dev/null || true

systemctl daemon-reload
systemctl enable unified-egregore.service
systemctl restart unified-egregore.service

echo "Waiting for :8100..."
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -sf "http://127.0.0.1:8100/health" >/dev/null 2>&1; then
    break
  fi
  sleep 3
done

curl -sf "http://127.0.0.1:8100/health" || echo "health failed"
echo ""
curl -sf "http://127.0.0.1:8100/egregores/available" || true
echo ""
