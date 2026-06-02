#!/usr/bin/env bash
# Reclaim space on pve-root. ComfyUI code/models already live on /mnt/s2-data (see below).
set -euo pipefail

S2="${S2_DATA:-/mnt/s2-data}"
FREED=0

log() { echo "[$(date -Iseconds)] $*"; }

du_root() { df -h / | tail -1; }

move_to_s2() {
  local src="$1"
  local name="${2:-$(basename "$src")}"
  local dest="$S2/$name"
  if [[ ! -e "$src" ]] || [[ -L "$src" ]]; then
    return 0
  fi
  if [[ -e "$dest" ]]; then
    log "SKIP move $src — $dest already exists"
    return 0
  fi
  log "Moving $src -> $dest"
  mv "$src" "$dest"
  ln -sfn "$dest" "$src"
}

log "Before: $(du_root)"

# Safe deletes (staging / temp)
for path in \
  /root/ollama-s2-ake-lora \
  /tmp/s2forge-build \
  /tmp/s2forge-web-deploy; do
  if [[ -d "$path" ]]; then
    sz="$(du -sh "$path" 2>/dev/null | cut -f1)"
    log "Removing $path ($sz)"
    rm -rf "$path"
  fi
done

# Oversized logs
for f in /var/log/s2-full-pipeline.log /var/log/s2-bitnet-lane-refresh.log /var/log/s2-qvac-bitnet-gpu-build.log; do
  if [[ -f "$f" ]] && [[ "$(stat -c%s "$f" 2>/dev/null || echo 0)" -gt 50000000 ]]; then
    : >"$f"
    log "Truncated $f"
  fi
done

journalctl --vacuum-size=150M 2>/dev/null || true

# Finetune checkpoints on root
find /root /opt/qvac-fabric-llm.cpp -maxdepth 5 -type d -name checkpoints 2>/dev/null | while read -r d; do
  ls -1dt "$d"/checkpoint_step_* 2>/dev/null | tail -n +3 | xargs -r rm -rf
done

# Docker: unused images (containers may be stopped Supabase stack)
if command -v docker >/dev/null 2>&1; then
  log "Docker before: $(docker system df 2>/dev/null | head -3 || true)"
  docker image prune -af 2>/dev/null || true
  docker container prune -f 2>/dev/null || true
fi

# Large trees → /mnt/s2-data (systemd paths under /root/... still work via symlink)
move_to_s2 /root/ninefold-studio-clean
move_to_s2 /root/demucs-venv
move_to_s2 /srv/s2-marketing-automation

log "ComfyUI: $(readlink -f /opt/ComfyUI 2>/dev/null || echo missing)"
log "After: $(du_root)"
log "Done."
