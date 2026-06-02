#!/usr/bin/env bash
# Full BitNet lane refresh: GPU QVAC → expanded dataset → train → deploy → smoke.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
QVAC_ROOT="${QVAC_ROOT:-/opt/qvac-fabric-llm.cpp}"
TQ2="${BITNET_QVAC_MODEL:-$QVAC_ROOT/models/BitNet-b1.58-2B-4T-tq2/dl-gianni-cor/bitnet_b1_58-xl-TQ2_0/bitnet_b1_58-xl-TQ2_0.gguf}"
PROMPTS="$API/training_data/bitnet-specialist-prompts-expanded.json"
DATASET="$EG/training_data/bitnet_specialist.jsonl"
LOG="${LOG:-/var/log/s2-bitnet-lane-refresh.log}"

exec > >(tee -a "$LOG") 2>&1
echo "=== $(date -Iseconds) BitNet lane refresh ==="

bash "$API/scripts/stabilize-hosted-inference-r730.sh"

echo "=== 1. GPU QVAC build ==="
bash "$API/scripts/setup-qvac-bitnet-gpu-r730.sh"

echo "=== 2. Expand specialist prompts ==="
python3 "$API/scripts/build-bitnet-specialist-prompts.py" \
  --out "$PROMPTS" \
  --merge-seed \
  --seed-path "$API/training_data/bitnet-specialist-prompts.json"

echo "=== 3. Distill dataset from Ollama teacher ==="
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  echo "Waiting for Ollama ($i/30)..."
  systemctl start ollama 2>/dev/null || true
  sleep 2
done
if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "ERROR: Ollama not reachable before distill"
  exit 1
fi
python3 "$API/scripts/build-bitnet-specialist-dataset.py" \
  --prompts "$PROMPTS" \
  --out "$DATASET" \
  --model s2-ake-lora \
  --sleep 0.2 \
  --timeout "${DISTILL_TIMEOUT:-600}"

ROWS="$(wc -l < "$DATASET" | tr -d ' ')"
if [[ "${ROWS:-0}" -lt 10 ]]; then
  echo "ERROR: distill produced only ${ROWS:-0} rows — aborting train"
  exit 1
fi
echo "Distill OK: $ROWS rows"

echo "=== 4. Train LoRA ==="
BITNET_TRAIN_JSONL="$DATASET" \
BITNET_MODEL_GGUF="$TQ2" \
LORA_EPOCHS="${LORA_EPOCHS:-3}" \
bash "$API/scripts/train-bitnet-lora-r730.sh"

echo "Waiting for train..."
while pgrep -f 'llama-finetune-lora.*bitnet_specialist' >/dev/null 2>&1; do
  sleep 30
  tail -1 /var/log/s2-bitnet-lora-train.log 2>/dev/null || true
done

ADAPTER="$EG/training_data/bitnet_ake_lora.gguf"
if [[ ! -f "$ADAPTER" ]]; then
  echo "ERROR: train did not produce $ADAPTER"
  tail -40 /var/log/s2-bitnet-lora-train.log
  exit 1
fi

echo "=== 5. Deploy + smoke ==="
BITNET_QVAC_MODEL_PATH="$TQ2" \
bash "$API/scripts/deploy-bitnet-finetuned-r730.sh"

python3 "$API/scripts/smoke-bitnet-sidecar-r730.py" || true
bash "$API/scripts/stabilize-hosted-inference-r730.sh"

echo "=== Done ==="
