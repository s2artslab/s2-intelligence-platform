#!/usr/bin/env bash
# Smoke dual-lane egregore routing on r730 (hosted fallback when no BitNet adapter).
set -euo pipefail
GW="${GW:-http://127.0.0.1:3020}"
EG="${EGREGORE_ID:-rhys}"
PAYLOAD=$(python3 - <<PY
import json
print(json.dumps({
    "egregore_id": "$EG",
    "task_class": "compact",
    "text": "Name one architectural principle in one sentence.",
}))
PY
)
echo "=== GET /api/public/egregore/inference ==="
curl -sf "$GW/api/public/egregore/inference" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('egregores:', len(d.get('egregores', [])))
for e in d.get('egregores', [])[:5]:
    lanes = e.get('lanes', {})
    print(' ', e.get('egregore_id'), 'hosted=', lanes.get('hosted'), 'bitnet=', lanes.get('bitnet'))
"
echo "=== POST /api/public/chat (X-S2-Inference-Lane: auto) egregore=$EG ==="
curl -s -m 300 -X POST "$GW/api/public/chat" \
  -H "Content-Type: application/json" \
  -H "X-S2-Inference-Lane: auto" \
  -d "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('success:', d.get('success'))
print('inference_lane:', d.get('inference_lane'))
print('egregore_id:', d.get('egregore_id'))
print('bitnet_adapter_ready:', d.get('bitnet_adapter_ready'))
print('source:', d.get('source'))
print('content:', (d.get('content') or d.get('error') or '')[:300])
"
echo "=== POST /api/research/bitnet/infer (bitnet lane, no billing) ==="
curl -s -m 90 -X POST "$GW/api/research/bitnet/infer" \
  -H "Content-Type: application/json" \
  -H "X-S2-Inference-Lane: bitnet" \
  -d "$PAYLOAD" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('ok:', d.get('ok', d.get('success')))
print('lane:', d.get('lane', d.get('inference_lane')))
print('egregore_id:', d.get('egregore_id'))
print('content:', (d.get('content') or d.get('response') or d.get('error') or '')[:300])
"
