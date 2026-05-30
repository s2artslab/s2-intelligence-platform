#!/usr/bin/env bash
# Populate Ninefold egregore training data with Mind Games strength-first content on r730.
set -euo pipefail

R730="${R730_HOST:-192.168.1.78}"
SSH_KEY="${R730_SSH_KEY:-$HOME/.ssh/id_ed25519_proxmox}"
NINEFOLD_DIR="${NINEFOLD_DIR:-/opt/ninefold-studio-clean}"

echo "==> Mind Games strength training populator on r730 ($R730)"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new "root@${R730}" bash -s <<EOF
set -euo pipefail
cd ${NINEFOLD_DIR}
if [[ ! -f scripts/populate_mind_games_enhancement_training.py ]]; then
  echo "Missing populate script at ${NINEFOLD_DIR}/scripts/populate_mind_games_enhancement_training.py"
  exit 1
fi
python3 scripts/populate_mind_games_enhancement_training.py
echo "Done — neurodivergent_strengths domain included in population run."
EOF
