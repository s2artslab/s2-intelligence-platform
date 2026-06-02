#!/usr/bin/env bash
# Operator wrapper — run full media inventory on r730.
set -euo pipefail
SCRIPT="${R730_MEDIA_INVENTORY_SCRIPT:-/root/ninefold-studio-clean/egregorelab/scripts/r730-media-inventory.sh}"
if [[ -x "$SCRIPT" ]]; then
  exec bash "$SCRIPT"
fi
if [[ -x "/opt/s2-ecosystem/public-api/scripts/../ninefold/egregorelab/scripts/r730-media-inventory.sh" ]]; then
  exec bash "/opt/s2-ecosystem/public-api/scripts/../ninefold/egregorelab/scripts/r730-media-inventory.sh"
fi
echo "Deploy ninefold-studio-clean to r730, then run:"
echo "  bash egregorelab/scripts/r730-media-inventory.sh"
exit 1
