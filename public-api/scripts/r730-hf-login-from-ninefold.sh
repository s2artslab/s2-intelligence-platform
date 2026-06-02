#!/usr/bin/env bash
# Load HF token from Ninefold Studio egregorelab .env and login on r730.
set -euo pipefail

ENV="${NINEFOLD_ENV:-/root/ninefold-studio-clean/egregorelab/.env}"
API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"

if [[ ! -f "$ENV" ]]; then
  echo "ERROR: Ninefold env not found: $ENV"
  exit 1
fi

# Normalize CRLF and optional `export` prefix, then source.
set -a
# shellcheck disable=SC1090
source <(sed 's/\r$//' "$ENV" | sed 's/^export //')
set +a

TOKEN="${HUGGINGFACE_API_KEY:-${HF_TOKEN:-}}"
TOKEN="$(echo -n "$TOKEN" | tr -d '[:space:]')"
if [[ -z "$TOKEN" ]]; then
  echo "ERROR: HUGGINGFACE_API_KEY / HF_TOKEN not set in $ENV"
  exit 1
fi

HF_TOKEN="$TOKEN" bash "$API/scripts/r730-hf-login.sh"
echo "HF auth OK (Ninefold Studio)"
