#!/usr/bin/env bash
# Keep Ollama hosted path stable on P40 (ComfyUI Conflicts=ollama.service).
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
ENV_FILE="${ENV_FILE:-$API/.env}"

echo "=== Stabilize hosted inference (Ollama vs ComfyUI) ==="

bash "$API/scripts/setup-r730-gpu-lane-policy-r730.sh" hosted
sleep 2

if ! systemctl is-active --quiet ollama; then
  echo "ERROR: ollama failed to start"
  journalctl -u ollama -n 20 --no-pager
  exit 1
fi

# Strip CRLF from .env (Windows sync)
sed -i 's/\r$//' "$ENV_FILE" 2>/dev/null || true

for kv in \
  "OLLAMA_LORA_MODEL=s2-ake-lora" \
  "OLLAMA_PREFER_LORA=true"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${kv}|" "$ENV_FILE"
  else
    echo "$kv" >>"$ENV_FILE"
  fi
done

systemctl restart s2-public-api 2>/dev/null || systemctl restart s2-intelligence-public-api 2>/dev/null || true
sleep 2

echo "=== Health ==="
curl -sf http://127.0.0.1:3020/health | python3 -m json.tool | grep -E 'activeModel|preferLora|hosted_inference|ollama' || true
ollama list || true

echo "ComfyUI: $(systemctl is-active comfyui 2>/dev/null || echo inactive)"
echo "Ollama: $(systemctl is-active ollama)"
echo "Done."
