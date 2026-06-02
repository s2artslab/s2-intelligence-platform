# Lab LoRA window (r730 P40)

**Purpose:** Fast unified Ake at [https://api.s2artslab.com/lab/ake-unified-lora](https://api.s2artslab.com/lab/ake-unified-lora) on one Tesla P40 without buying another GPU.

**Deep key:** ComfyUI **files** live on `/mnt/s2-data` (~3 TB). ComfyUI **inference** still uses the same P40. Lab LoRA needs VRAM — pause Comfy for the window.

---

## One command — window ON

```bash
bash /opt/s2-ecosystem/public-api/scripts/lab-lora-window-on-r730.sh
```

This will:

1. Stop `comfyui.service` (disk unchanged under `/mnt/s2-data/comfyui`)
2. End Tier C train process if log shows epoch 2.0 but process is stuck
3. Apply **4-bit CUDA** unified serve (`EGREGORE_LOAD_IN_4BIT=1`, P40 venv)
4. Smoke-test `/health` and `/generate`

Confirm health:

```bash
curl -s http://127.0.0.1:8100/health
# expect: "device": "cuda", "load_in_4bit": true
```

---

## One command — window OFF

```bash
bash /opt/s2-ecosystem/public-api/scripts/lab-lora-window-off-r730.sh
```

This will:

1. Restore unified **CPU** lab mode (`setup-unified-production-r730.sh`)
2. Restart ComfyUI if it was running before the window

---

## Lab UI quality (important)

Current **Tier C LoRA** weights over-learned template openers (`In the context of…`, `From a synthesis perspective…`) from `ake_tier_c_blended.json`. Prompt fixes help but **do not** fully fix the adapter.

The lab page defaults to **Ollama `s2-ake`** (production voice) for conversation. Uncheck only to benchmark raw LoRA.

Ollama must be running on r730:

```bash
systemctl start ollama
curl -s http://127.0.0.1:11434/api/tags | head
```

## Status

```bash
bash /opt/s2-ecosystem/public-api/scripts/lab-lora-window-status-r730.sh
```

## After 4-bit is healthy

```bash
python3 /opt/s2-ecosystem/public-api/scripts/test-lab-chat-r730.py
python3 /opt/s2-ecosystem/public-api/scripts/tier-c-eval-gate-r730.py \
  --lab-chat --skip-gateway
```

`--lab-chat` exercises the same path as [the lab UI](https://api.s2artslab.com/lab/ake-unified-lora) (no billing).  
Do **not** set `HOSTED_PREFER_UNIFIED_LORA=true` until the gate exits 0 **and** you have operator sign-off (short-prompt voice may still need Tier C quality review — responses can be generic).

**Gate passed (2026-05-26):** `tier-c-eval-gate-r730.py --lab-chat --skip-gateway` → exit 0.

---

## GPU layout (single P40)

| Workload | Typical VRAM | Lab window |
|----------|--------------|------------|
| ComfyUI Flux | ~12 GB | **Stopped** |
| Tier C QLoRA train | ~8–9 GB | **Must not run** during serve |
| Unified 4-bit Ake | ~6–8 GB | **Active** |

---

## Deploy scripts to r730

Copy from workstation, then fix line endings on the host (**use `sed -i 's/\r$//'` only** — never `tr -d r`):

```bash
sed -i 's/\r$//' /opt/s2-ecosystem/public-api/scripts/lab-lora-window-*.sh \
  /opt/s2-ecosystem/public-api/scripts/setup-unified-4bit-r730.sh
```

---

## Related

- [R730_UNIFIED_MEMORY_PLAN.md](./R730_UNIFIED_MEMORY_PLAN.md)
- [AKE_LORA_STATUS.md](./AKE_LORA_STATUS.md)
- `enable-unified-4bit-after-tier-c-r730.sh` — auto-wait variant (optional; prefer lab window script)
