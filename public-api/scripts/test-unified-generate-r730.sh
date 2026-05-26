#!/usr/bin/env bash
set -euo pipefail
curl -sf -m 180 -X POST http://127.0.0.1:8100/generate \
  -H 'Content-Type: application/json' \
  -d '{"egregore":"ake","prompt":"Say hello in one short sentence.","max_length":60,"temperature":0.35}'
echo
