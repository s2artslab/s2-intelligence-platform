#!/usr/bin/env bash
# Apply Ollama systemd overrides on r730 for GPU session + Cursor CORS.
# Run on r730 as root:
#   bash scripts/r730-apply-ollama-cursor-env.sh

set -euo pipefail

DROPIN_DIR="/etc/systemd/system/ollama.service.d"
DROPIN_FILE="${DROPIN_DIR}/cursor-r730.conf"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GPU_TEMPLATE="${SCRIPT_DIR}/../../../ninefold-studio-clean/deploy/ollama-gpu-media.conf"

mkdir -p "${DROPIN_DIR}"

cat > "${DROPIN_FILE}" <<'EOF'
[Service]
Environment=OLLAMA_HOST=0.0.0.0:11434
Environment=OLLAMA_ORIGINS=*
Environment=OLLAMA_KEEP_ALIVE=30m
Environment=OLLAMA_MAX_LOADED_MODELS=1
EOF

# If gpu-media.conf also sets OLLAMA_KEEP_ALIVE, edit that file too (later drop-ins win).
GPU_MEDIA="/etc/systemd/system/ollama.service.d/gpu-media.conf"
if [[ -f "${GPU_MEDIA}" ]]; then
  sed -i 's/OLLAMA_KEEP_ALIVE=.*/OLLAMA_KEEP_ALIVE=30m/' "${GPU_MEDIA}" || true
  echo "Updated ${GPU_MEDIA} keep-alive for Cursor sessions"
fi

systemctl daemon-reload
systemctl restart ollama.service
sleep 2
systemctl is-active ollama.service
echo "Ollama cursor-r730 drop-in applied: ${DROPIN_FILE}"
