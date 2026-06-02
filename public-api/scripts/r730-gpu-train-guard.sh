#!/usr/bin/env bash
# Keep ComfyUI off the GPU during long QLoRA / BitNet trains.
# ComfyUI unit has Restart=always — systemctl stop alone is not enough.
#
#   . "$API/scripts/r730-gpu-train-guard.sh"
#   r730_pause_comfyui_for_gpu_train
#   ... train ...
#   r730_resume_comfyui_after_gpu_train   # optional; leave masked until train exits

r730_pause_comfyui_for_gpu_train() {
  systemctl stop comfyui unified-egregore bitnet-sidecar 2>/dev/null || true
  systemctl mask --runtime comfyui 2>/dev/null || true
  sleep 2
  pkill -f '/opt/ComfyUI/venv/bin/python main.py' 2>/dev/null || true
  sleep 1
}

# Free P40 for QVAC llama-finetune-lora (-ngl). Ollama + sidecar conflict on single GPU.
r730_prepare_p40_for_bitnet_train() {
  r730_pause_comfyui_for_gpu_train
  systemctl stop ollama 2>/dev/null || true
  sleep 2
  pkill -f 'llama-cli.*qvac-fabric' 2>/dev/null || true
  pkill -f 'llama-finetune-lora' 2>/dev/null || true
  sleep 1
}

r730_restore_hosted_after_bitnet_train() {
  r730_resume_comfyui_after_gpu_train
  systemctl start ollama bitnet-sidecar 2>/dev/null || true
}

r730_resume_comfyui_after_gpu_train() {
  systemctl unmask comfyui 2>/dev/null || true
}

r730_qlora_train_complete_in_log() {
  local log="${1:-/var/log/s2-ake-proper-blend-train.log}"
  [[ -f "$log" ]] && grep -qE 'epoch.*2\.0|100%.*4874/4874|Training completed' "$log" 2>/dev/null
}
