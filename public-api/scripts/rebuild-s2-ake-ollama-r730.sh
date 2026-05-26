#!/usr/bin/env bash
# Rebuild s2-ake on r730: pull base, apply Modelfile, smoke test.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${OLLAMA_BASE_MODEL:-llama3.1:8b}"
MODEL="${OLLAMA_MODEL_NAME:-s2-ake}"

echo "Pulling base: $BASE ..."
ollama pull "$BASE"

echo "Creating $MODEL from Modelfile.s2-ake ..."
ollama create "$MODEL" -f "$ROOT/ollama/Modelfile.s2-ake"

echo "Models:"
ollama list | grep -E "$MODEL|$BASE" || ollama list

echo "Smoke test ..."
curl -sf http://127.0.0.1:11434/api/chat -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hi in one sentence.\"}],\"stream\":false}" | head -c 200
echo

echo "Done. Restart gateway if env changed: systemctl restart s2-public-api"
