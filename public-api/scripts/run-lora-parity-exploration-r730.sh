#!/usr/bin/env bash
# LoRA ↔ Ollama parity exploration: drop-before-strip audit, distill, ablation, raw vs stripped eval.
set -euo pipefail

API="${PUBLIC_API_DIR:-/opt/s2-ecosystem/public-api}"
EG="${EGREGORE_TRAINING_DIR:-/opt/s2-ecosystem/egregore-training}"
LOG="${LOG:-/var/log/s2-lora-parity-exploration.log}"

exec > >(tee -a "$LOG") 2>&1
echo "=== LoRA parity exploration $(date -Iseconds) ==="

echo "=== Phase 0: drop-before-strip audit (compare to v3) ==="
python3 "$API/scripts/audit-ake-assistant-quality.py" \
  --input "$EG/training_data/ake_tier_c_blended.json" \
  --drop-canned --strip-openers --min-score 0.4 \
  --out "$EG/training_data/ake_tier_c_cleaned_v4.json"

echo "=== Phase 1: Ollama distill pilot (all prompts in lora-distill-prompts.json) ==="
systemctl is-active ollama >/dev/null || systemctl start ollama
sleep 2
python3 "$API/scripts/build-tier-c-ollama-distill.py" \
  --prompts "$API/training_data/lora-distill-prompts.json" \
  --out "$EG/training_data/ake_tier_c_ollama_distill.jsonl" \
  --ollama-url http://127.0.0.1:11434 --model s2-ake

echo "=== Phase 2: prompt mode ablation ==="
python3 "$API/scripts/test-unified-prompt-ablation-r730.py" | tee /var/log/s2-lora-prompt-ablation.log

echo "=== Phase 3a: eval gate (with serve-time cleanup) ==="
python3 "$API/scripts/tier-c-eval-gate-r730.py" --lab-chat --skip-gateway \
  | tee /var/log/s2-tier-c-eval-with-cleanup.log || true

echo "=== Phase 3b: eval gate RAW LoRA (no response cleanup) ==="
python3 "$API/scripts/tier-c-eval-gate-r730.py" --lab-chat --skip-gateway --raw-lora \
  | tee /var/log/s2-tier-c-eval-raw-lora.log || true

echo "=== Phase 4: LoRA vs Ollama comparison ==="
python3 "$API/scripts/compare-lora-vs-ollama-r730.py" | tee /var/log/s2-lora-vs-ollama.log

echo "=== Done. Logs: $LOG ==="
