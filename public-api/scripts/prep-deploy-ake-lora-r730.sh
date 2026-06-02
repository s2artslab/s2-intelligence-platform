#!/usr/bin/env bash
# Preflight before Ollama s2-ake-lora deploy (run while train finishes or after).
set -euo pipefail

ADAPTER="${LORA_ADAPTER_PATH:-/mnt/bipra/egregore-training/trained_models/ake-llama32}"
ERR=0

check() {
  if "$@"; then
    echo "OK  $*"
  else
    echo "FAIL $*"
    ERR=1
  fi
}

echo "=== Prep deploy s2-ake-lora ==="

systemctl is-active ollama >/dev/null 2>&1 && echo "OK  ollama active" || { echo "FAIL ollama inactive"; ERR=1; }

if ollama list 2>/dev/null | grep -q 'llama3.2'; then
  echo "OK  ollama has llama3.2 base"
else
  echo "FAIL missing llama3.2 — run: ollama pull llama3.2"
  ERR=1
fi

if [[ -f "$ADAPTER/adapter_config.json" ]]; then
  echo "OK  adapter at $ADAPTER"
else
  echo "WARN adapter not ready yet ($ADAPTER) — train still running?"
fi

df -h /mnt/bipra 2>/dev/null | tail -1 || true
check test -d /opt/s2-ecosystem/public-api/scripts

echo "=== Prep done (exit $ERR) ==="
exit "$ERR"
