#!/usr/bin/env bash
# Coordinated GPU lane policy on P40: hosted (Ollama) vs media (ComfyUI).
# Replaces one-sided systemd Conflicts= that silently stops Ollama when Comfy restarts.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
MODE="${1:-hosted}"
COMFY_DROPIN=/etc/systemd/system/comfyui.service.d/gpu-media.conf
STATE=/var/lib/s2-ecosystem/gpu-lane-mode

usage() {
  cat <<EOF
Usage: $0 {hosted|media|status}

  hosted  — Ollama + gateway voice (default production). ComfyUI stopped + masked.
  media   — ComfyUI for FLUX/SVD. Ollama stopped. Use lab-lora-window-off to restore hosted.
  status  — Show active lane and unit states.

Symlinks (/opt/ComfyUI, /opt/s2-ecosystem, etc.) are unchanged; apps keep the same paths.
EOF
}

lane_status() {
  echo "mode: $(cat "$STATE" 2>/dev/null || echo unknown)"
  echo "ollama: $(systemctl is-active ollama 2>/dev/null || echo inactive)"
  echo "comfyui: $(systemctl is-active comfyui 2>/dev/null || echo inactive)"
  echo "bitnet-sidecar: $(systemctl is-active bitnet-sidecar 2>/dev/null || echo inactive)"
  if [[ -f "$COMFY_DROPIN" ]]; then
    echo "comfy drop-in:"
    grep -E 'Conflicts|After|Wants' "$COMFY_DROPIN" 2>/dev/null || true
  fi
}

install_comfy_dropin_no_conflict() {
  mkdir -p "$(dirname "$COMFY_DROPIN")"
  if [[ -f "$COMFY_DROPIN" ]] && ! grep -q 'managed by setup-r730-gpu-lane-policy' "$COMFY_DROPIN" 2>/dev/null; then
    cp -a "$COMFY_DROPIN" "${COMFY_DROPIN}.bak.$(date +%Y%m%d)"
  fi
  cat >"$COMFY_DROPIN" <<'EOF'
# Managed by setup-r730-gpu-lane-policy-r730.sh — do not add Conflicts=ollama.service.
# Use: bash .../setup-r730-gpu-lane-policy-r730.sh {hosted|media}
[Unit]
After=network-online.target
Wants=network-online.target
EOF
  systemctl daemon-reload
}

case "$MODE" in
  status)
    lane_status
    exit 0
    ;;
  hosted)
    install_comfy_dropin_no_conflict
    # shellcheck source=r730-gpu-train-guard.sh
    . "$API/scripts/r730-gpu-train-guard.sh"
    r730_pause_comfyui_for_gpu_train
    systemctl enable ollama 2>/dev/null || true
    systemctl start ollama 2>/dev/null || true
    systemctl start bitnet-sidecar 2>/dev/null || true
    systemctl restart s2-public-api 2>/dev/null || true
    mkdir -p "$(dirname "$STATE")"
    echo hosted >"$STATE"
  echo "=== Hosted lane active ==="
    lane_status
    ;;
  media)
    install_comfy_dropin_no_conflict
    systemctl stop ollama bitnet-sidecar 2>/dev/null || true
    systemctl unmask comfyui 2>/dev/null || true
    systemctl enable comfyui 2>/dev/null || true
    systemctl start comfyui 2>/dev/null || true
    mkdir -p "$(dirname "$STATE")"
    echo media >"$STATE"
    echo "=== Media lane active (ComfyUI) ==="
    lane_status
    ;;
  *)
    usage
    exit 1
    ;;
esac
