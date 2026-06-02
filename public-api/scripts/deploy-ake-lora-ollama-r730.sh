#!/usr/bin/env bash
# Deploy Llama 3.2 QLoRA adapter into Ollama as s2-ake-lora (fast hosted path).
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
ADAPTER_SRC="${LORA_ADAPTER_PATH:-/mnt/bipra/egregore-training/trained_models/ake-llama32}"
GGUF_DIR="${GGUF_OUT_DIR:-$ADAPTER_SRC/gguf}"
ENV_FILE="${ENV_FILE:-/opt/s2-ecosystem/public-api/.env}"
PREFER_LORA="${OLLAMA_PREFER_LORA:-false}"
PYTHON="${PYTHON:-/opt/s2-ecosystem/venv-vllm-p40-src/bin/python}"
LLAMA_CPP="${LLAMA_CPP:-/opt/llama.cpp}"
QUANT="${GGUF_QUANT:-q4_k_m}"
MERGE_LOG="${MERGE_LOG:-/var/log/s2-ake-lora-merge-gguf.log}"

if [[ ! -f "$ADAPTER_SRC/adapter_config.json" ]]; then
  echo "ERROR: No adapter at $ADAPTER_SRC — run train-ake-llama32-qlora-r730.sh first"
  exit 1
fi

systemctl start ollama 2>/dev/null || true
sleep 2

resolve_gguf() {
  if [[ -n "${GGUF_PATH:-}" && -f "$GGUF_PATH" ]]; then
    echo "$GGUF_PATH"
    return 0
  fi
  local manifest="$GGUF_DIR/manifest.json"
  if [[ -f "$manifest" ]]; then
    "$PYTHON" -c "import json,sys; print(json.load(open(sys.argv[1]))['gguf'])" "$manifest"
    return 0
  fi
  local candidate="$GGUF_DIR/s2-ake-lora-${QUANT}.gguf"
  if [[ -f "$candidate" ]]; then
    echo "$candidate"
    return 0
  fi
  return 1
}

create_via_gguf() {
  local gguf="$1"
  echo "=== Create Ollama s2-ake-lora from merged GGUF ==="
  echo "GGUF: $gguf"
  bash "$API/scripts/create-s2-ake-lora-r730.sh" --gguf "$gguf"
}

merge_to_gguf() {
  echo "=== Merge LoRA → HF weights (GGUF convert optional) ==="
  mkdir -p "$GGUF_DIR"
  ADAPTER_SRC="$ADAPTER_SRC" GGUF_DIR="$GGUF_DIR" "$PYTHON" - <<'PY' 2>&1 | tee -a "$MERGE_LOG"
import os
import sys
from pathlib import Path

adapter = Path(os.environ["ADAPTER_SRC"])
merged = Path(os.environ["GGUF_DIR"]) / "merged-hf"
if (merged / "model.safetensors.index.json").exists():
    print(f"Merged HF already exists: {merged}")
    sys.exit(0)
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

print("Loading base + LoRA and merging...")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B-Instruct", trust_remote_code=True)
base = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.2-3B-Instruct",
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
)
model = PeftModel.from_pretrained(base, str(adapter))
merged_model = model.merge_and_unload()
merged.mkdir(parents=True, exist_ok=True)
merged_model.save_pretrained(merged)
tokenizer.save_pretrained(merged)
print(f"Merged HF saved: {merged}")
PY
}

create_via_merged_hf() {
  echo "=== Create Ollama s2-ake-lora from merged HF ==="
  MERGED_HF_SRC="$GGUF_DIR/merged-hf" bash "$API/scripts/create-s2-ake-lora-from-merged-hf-r730.sh"
}

echo "=== Deploy s2-ake-lora ==="
if LORA_ADAPTER_PATH="$ADAPTER_SRC" bash "$API/scripts/create-s2-ake-lora-r730.sh" --adapter 2>/tmp/s2-ake-lora-adapter-create.log; then
  echo "Created via safetensors ADAPTER"
else
  echo "WARN: safetensors ADAPTER create failed — see /tmp/s2-ake-lora-adapter-create.log"
  tail -5 /tmp/s2-ake-lora-adapter-create.log || true
  if gguf="$(resolve_gguf 2>/dev/null)"; then
    create_via_gguf "$gguf"
  else
    merge_to_gguf
    create_via_merged_hf
  fi
fi

echo "=== Smoke test s2-ake-lora ==="
curl -sf -m 120 http://127.0.0.1:11434/api/chat -d '{
  "model": "s2-ake-lora",
  "messages": [{"role":"user","content":"What is a motion to dismiss?"}],
  "stream": false,
  "options": {"temperature": 0.2}
}' | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('message') or {}).get('content','')[:300])"

touch "$ENV_FILE"
for kv in \
  "OLLAMA_LORA_MODEL=s2-ake-lora" \
  "OLLAMA_PREFER_LORA=$PREFER_LORA"; do
  key="${kv%%=*}"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${kv}|" "$ENV_FILE"
  else
    echo "$kv" >> "$ENV_FILE"
  fi
done

if [[ "$PREFER_LORA" == "true" ]]; then
  if grep -q '^HOSTED_PREFER_UNIFIED_LORA=' "$ENV_FILE"; then
    sed -i 's/^HOSTED_PREFER_UNIFIED_LORA=.*/HOSTED_PREFER_UNIFIED_LORA=false/' "$ENV_FILE"
  fi
  echo "Set OLLAMA_PREFER_LORA=true — hosted uses Ollama s2-ake-lora (fast, trained weights)"
fi

systemctl restart s2-public-api 2>/dev/null || systemctl restart s2-intelligence-public-api 2>/dev/null || true
sleep 2
curl -sf -m 10 http://127.0.0.1:3020/health | python3 -m json.tool | grep -E 'hosted|ollama|preferLora|activeModel' || true

echo "Done. To prefer LoRA in production: OLLAMA_PREFER_LORA=true bash $0"
