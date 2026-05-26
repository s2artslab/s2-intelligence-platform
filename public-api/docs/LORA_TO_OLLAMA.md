# LoRA → Ollama (`s2-ake-lora`)

**Not production until 7B Tier C weights exist** — see [AKE_LORA_STATUS.md](./AKE_LORA_STATUS.md). Hosted users use `s2-ake` (prompt-only Llama) today.

Two ways to run trained Ake LoRA inside Ollama for the hosted gateway.

## Prerequisites

- Base model on Ollama: `llama3.2` (or same HF id as training base)
- Trained LoRA directory with `adapter_config.json` + `adapter_model.safetensors`
- Default adapter path on r730: `/opt/s2-ecosystem/egregore-training/ake/models/lora`

Train first (on r730 GPU) using your existing pipeline under `/opt/s2-ecosystem/egregore-training/`.

---

## Path A — ADAPTER in Modelfile (recommended, no full merge)

Fastest: Ollama loads base + LoRA adapter at runtime.

```bash
# On r730 (where Ollama runs)
cd /opt/s2-ecosystem/public-api   # or sync this repo path
export LORA_ADAPTER_PATH=/opt/s2-ecosystem/egregore-training/ake/models/lora
bash scripts/create-s2-ake-lora-r730.sh --adapter
```

Creates **`s2-ake-lora`** in `ollama list`.

Modelfile concept:

```dockerfile
FROM llama3.2
ADAPTER /opt/s2-ecosystem/egregore-training/ake/models/lora
SYSTEM """...same S² assistant tone as s2-ake..."""
```

---

## Path B — Merge LoRA into one GGUF (single artifact)

Use when you want a standalone GGUF (easier to copy, no adapter path on disk).

```bash
# On r730 with GPU + Python venv (transformers, peft, torch)
cd public-api
python scripts/merge_lora_to_gguf.py \
  --base-model meta-llama/Llama-3.2-3B-Instruct \
  --adapter /opt/s2-ecosystem/egregore-training/ake/models/lora \
  --out-dir /opt/s2-ecosystem/egregore-training/ake/models/gguf \
  --quantize q4_k_m

bash scripts/create-s2-ake-lora-r730.sh --gguf /opt/s2-ecosystem/egregore-training/ake/models/gguf/s2-ake-lora-q4_k_m.gguf
```

Requires **llama.cpp** (`convert_hf_to_gguf.py`) on the host — installed at `/opt/llama.cpp` on r730.

---

## Wire into public-api

After `ollama create s2-ake-lora`:

```env
OLLAMA_MODEL=s2-ake-lora
# Or prefer LoRA when present, fallback to prompt-only:
OLLAMA_MODEL=s2-ake
OLLAMA_LORA_MODEL=s2-ake-lora
OLLAMA_PREFER_LORA=true
```

Restart `npm start`. `/health` reports which model is active.

---

## Verify

```bash
ollama list | grep s2-ake
curl http://127.0.0.1:11434/api/chat -d '{
  "model": "s2-ake-lora",
  "messages": [{"role":"user","content":"Say hello in one sentence."}],
  "stream": false
}'
```

---

## Current status (check r730)

```bash
ls -la /opt/s2-ecosystem/egregore-training/ake/models/lora/
```

If empty, Path A/B cannot run until training exports adapters. Until then the gateway uses **`s2-ake`** (Modelfile system prompt only).

**Stack warning:** BIPRA GPT-2 checkpoints cannot merge into Llama Ollama. Use 7B adapters from Tier C retrain ([TIER_C_RETRAIN_RUNBOOK.md](./TIER_C_RETRAIN_RUNBOOK.md)).
