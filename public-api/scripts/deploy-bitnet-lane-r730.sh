#!/usr/bin/env bash
# Full BitNet experimental lane deploy on r730 (after sync from workstation).
# Run on r730 as root:
#   bash /opt/s2-ecosystem/public-api/scripts/deploy-bitnet-lane-r730.sh
#   BITNET_STUB=1 bash .../deploy-bitnet-lane-r730.sh
set -euo pipefail

ROOT="${ROOT:-/opt/s2-ecosystem/public-api}"
STUB="${BITNET_STUB:-1}"

echo "== Deploy BitNet 1.58-bit experimental lane =="

bash "${ROOT}/scripts/setup-bitnet-sidecar-r730.sh"

# Ensure data dir for research metrics
mkdir -p "${ROOT}/data"
chmod 755 "${ROOT}/data" 2>/dev/null || true

# Restart gateway
if systemctl is-active s2-public-api.service &>/dev/null; then
  systemctl restart s2-public-api.service
  echo "Restarted s2-public-api.service"
elif systemctl is-active s2-intelligence-public-api.service &>/dev/null; then
  systemctl restart s2-intelligence-public-api.service
  echo "Restarted s2-intelligence-public-api.service"
else
  echo "WARN: no known gateway unit — restart public-api manually"
fi

sleep 2

echo "Gateway health (bitnet block):"
curl -sf "http://127.0.0.1:3020/health" | python3 -c "
import json,sys
d=json.load(sys.stdin)
b=d.get('bitnet',{})
print('  bitnet.ok:', b.get('ok'), 'enabled:', b.get('enabled'), 'stub:', b.get('stub_mode'))
" || echo "  WARN: gateway health failed"

echo "Research status:"
curl -sf "http://127.0.0.1:3020/api/research/bitnet/status" | python3 -m json.tool | head -30 || true

echo "Running benchmark..."
python3 "${ROOT}/scripts/bitnet-benchmark-r730.py" --gateway "http://127.0.0.1:3020" || {
  echo "WARN: benchmark failed (Ollama down or billing?)"
}

echo "Eval gate:"
python3 "${ROOT}/scripts/bitnet-eval-gate-r730.py" --gateway "http://127.0.0.1:3020" || {
  echo "WARN: eval gate not passed yet — expected until benchmark data exists"
}

echo "Done."
