#!/usr/bin/env bash
set -eu
BASE="${1:-http://127.0.0.1:3020}"

echo "== health =="
curl -sf "${BASE}/health" | head -c 200
echo

echo "== doc-intel health =="
curl -sf "${BASE}/api/public/document-intelligence/health"
echo

echo "== exploration paths (hosted) =="
curl -sf -X POST "${BASE}/api/psla/exploration/paths" \
  -H 'Content-Type: application/json' \
  -H 'X-S2-Inference: hosted' \
  -d '{"workspace_context":"Tenant dispute in California, not yet filed.","jurisdiction":"California"}' \
  | head -c 500
echo

echo "OK"
