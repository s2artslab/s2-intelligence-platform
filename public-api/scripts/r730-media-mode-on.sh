#!/usr/bin/env bash
# Wrapper — run full media window on r730.
set -euo pipefail
SCRIPT="${R730_MEDIA_MODE_SCRIPT:-/root/ninefold-studio-clean/scripts/r730-media-mode-on.sh}"
exec bash "$SCRIPT"
