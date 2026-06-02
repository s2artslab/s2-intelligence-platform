# r730 unified egregore — memory & device plan (Tesla P40)

**Host:** Proxmox r730 `192.168.1.78`  
**GPU:** Tesla P40 (24 GB VRAM, no bfloat16)  
**Service:** `unified-egregore` → `:8100`

---

## Modes

| Mode | Script | `EGREGORE_DEVICE` | `EGREGORE_LOAD_IN_4BIT` | Hosted users |
|------|--------|-------------------|-------------------------|--------------|
| **Production (default)** | `setup-unified-production-r730.sh` | `cpu` | `0` | Use **Ollama**; unified optional lab |
| **Lab 4-bit CUDA (preferred)** | `setup-unified-4bit-r730.sh` | `cuda` | `1` | ~6–8 GB VRAM; after Tier C train |
| **Lab 7B fp16 CUDA** | `setup-unified-7b-r730.sh` | `cuda` | `0` | **OOM risk** on P40 — avoid |
| **Legacy GPT-2** | `setup-unified-8100-r730.sh` | `cpu` | `0` | BIPRA GPT-2 weights only |

**Lab window (recommended):** `lab-lora-window-on-r730.sh` / `lab-lora-window-off-r730.sh` — see [LAB_LORA_WINDOW.md](./LAB_LORA_WINDOW.md).

Auto after Tier C: `enable-unified-4bit-after-tier-c-r730.sh` (waits for train; `STOP_COMFY=1` default).

\*Use 7B on CPU only for eval/benchmarks; expect 30s–120s per reply. Not for production hosted latency.

---

## Why unified LoRA often does not run

```mermaid
flowchart TD
  A[Gateway prefers unified] --> B{:8100 healthy?}
  B -->|7B CUDA| C[P40 OOM]
  B -->|CPU load| D[30s+ cold start]
  C --> E[unified_lora.ok false]
  D --> F[Gateway timeout 120–180s]
  E --> G[Fallback: Ollama s2-ake]
  F --> G
```

| Failure | Signal | Mitigation |
|---------|--------|------------|
| CUDA OOM | `journalctl -u unified-egregore` CUDA OOM | `setup-unified-production-r730.sh` → CPU |
| Slow CPU | `/health` ok but chat timeout | Raise `UNIFIED_EGREGORE_TIMEOUT_MS=300000` for lab only |
| Wrong weights | `hasAke: false` | Check `ADAPTERS_BASE=/mnt/bipra/egregore-training/trained_models` |
| Training holding GPU | Ollama works, unified fails | Wait for training end; restart service |

---

## Recommended production posture

```bash
# 1. Unified in safe CPU lab mode (for Tier C eval / benchmarks)
bash /opt/s2-ecosystem/public-api/scripts/setup-unified-production-r730.sh

# 2. Gateway: Ollama primary
grep HOSTED_PREFER_UNIFIED_LORA /opt/s2-ecosystem/public-api/.env
# → false

# 3. Ollama s2-ake always up
systemctl status ollama   # or your unit name
ollama list | grep s2-ake
```

---

## When to enable GPU lab serve (4-bit)

After Tier C `--qlora` train finishes and GPU has **≥10 GB free** (stop ComfyUI if needed):

```bash
bash /opt/s2-ecosystem/public-api/scripts/enable-unified-4bit-after-tier-c-r730.sh
# or directly:
bash /opt/s2-ecosystem/public-api/scripts/setup-unified-4bit-r730.sh
nvidia-smi
curl -s http://127.0.0.1:8100/health   # expect load_in_4bit: true, device: cuda
python3 /opt/s2-ecosystem/public-api/scripts/tier-c-eval-gate-r730.py --skip-ollama
```

Patch (idempotent): `apply-unified-4bit-inference-patch-r730.py` — mirrors `train_egregore_on_foundation_7b.py --qlora` BitsAndBytesConfig.

If OOM: `setup-unified-production-r730.sh` (CPU rollback). Do **not** use full fp16 `setup-unified-7b-r730.sh` on P40 unless experimenting.

---

## Env tuning (gateway)

| Variable | Lab CPU | Production hosted |
|----------|---------|-------------------|
| `HOSTED_PREFER_UNIFIED_LORA` | `false` until Tier C gate | `false` (then `true`) |
| `UNIFIED_EGREGORE_TIMEOUT_MS` | `180000`–`300000` | `120000` if unified enabled |
| `UNIFIED_HEALTH_TIMEOUT_MS` | `60000` | `60000` |

Template: [scripts/r730-public-api.env](../scripts/r730-public-api.env)

---

## systemd drop-ins

| File | Purpose |
|------|---------|
| `unified-egregore.service.d/tier-ab.conf` | Persona off, greedy, `egregore_only` |
| `unified-egregore.service.d/7b-cuda.conf` | CUDA 7B — **remove** for production safe mode |
| (created by production script) `production-safe.conf` | CPU, `HOSTED_PREFER` stays false |

---

## Related

- [AKE_LORA_STATUS.md](./AKE_LORA_STATUS.md)
- [TIER_C_RETRAIN_RUNBOOK.md](./TIER_C_RETRAIN_RUNBOOK.md)
