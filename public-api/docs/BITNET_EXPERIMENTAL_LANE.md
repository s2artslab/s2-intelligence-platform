# BitNet b1.58 experimental lane

**Status:** May 2026 (experimental organ — production spine remains 4-bit Ollama)  
**Claims:** BitNet quantization = **E** when deployed. Public “1.58D” = **M** (morphic policy, not weight format).

---

## Architecture

| Role | Model | Lane |
|------|-------|------|
| Main Ake synthesis | Ollama `s2-ake` / 4-bit unified LoRA | `hosted` |
| Specialist compact tasks | BitNet b1.58 2B4T via bitnet.cpp | `bitnet` |
| Routing / governance | `MORPHIC_RESONANCE` interval | ops knob (class M) |
| Future | Ake-distilled native BitNet | research target |

```
Gateway :3020
  ├─ /api/public/chat          → default hosted (4-bit Ollama)
  ├─ X-S2-Inference-Lane: compact → BitNet when BITNET_ENABLED
  └─ /api/research/bitnet/*    → metrics + benchmark ingest (S² Research)

Sidecar :8120 (CPU)
  └─ bitnet-sidecar-server.py → bitnet.cpp or stub mode
```

---

## Specialist task classes (BitNet-eligible)

`summary`, `classification`, `routing`, `tagging`, `compact`, `cheap_qa`

**Blocked:** `legal` context, `long_form`, `synthesis` voice, ensemble.

---

## r730 setup

```bash
# Full install (clone BitNet, download GGUF, systemd sidecar)
bash /opt/s2-ecosystem/public-api/scripts/setup-bitnet-sidecar-r730.sh

# Stub mode (no model — dev/CI)
BITNET_STUB=1 bash scripts/setup-bitnet-sidecar-r730.sh

# Benchmark + record runs for research
python3 scripts/bitnet-benchmark-r730.py --gateway http://127.0.0.1:3020

# Eval gate (after benchmark)
python3 scripts/bitnet-eval-gate-r730.py
```

---

## Environment

```env
BITNET_ENABLED=true
BITNET_BASE_URL=http://127.0.0.1:8120
BITNET_MODEL=bitnet-b1.58-2B-4T
BITNET_TIMEOUT_MS=120000
BITNET_RESEARCH_DATA_DIR=./data
```

---

## Research API (S² Research app polls these)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/research/bitnet/status` | Health + rolling summary |
| `GET /api/research/bitnet/runs` | Recent benchmark rows |
| `POST /api/research/bitnet/infer` | Single specialist infer (bitnet or baseline) |
| `POST /api/research/bitnet/record-batch` | Persist benchmark batch |

Opt in to BitNet on chat:

- Header: `X-S2-Inference-Lane: compact` | `bitnet` | `auto` | `hosted`
- Body: `{ "task_class": "summary", "text": "...", "egregore_id": "my_agent" }`

### EgregoreLab user egregores (dual lane)

User-generated egregores from EgregoreLab share the same routing:

| Lane | Backend | Notes |
|------|---------|--------|
| `hosted` | Ollama 4-bit + RAG | Persona from `unified_egregore_profiles.json` |
| `bitnet` | 1.58-bit sidecar + per-egregore LoRA | After `train-bitnet-custom-egregore-r730.sh` |
| `auto` | BitNet when adapter exists, else hosted | Recommended for EgregoreLab clients |

```bash
# After EgregoreLab saves a profile:
python3 scripts/export-egregorelab-inference-bundle.py --egregore my_agent

# On r730 — train LoRA and register adapter:
EGREGORE_ID=my_agent bash scripts/train-bitnet-custom-egregore-r730.sh
```

Gateway:

- `GET /api/public/egregore/inference` — list egregores + lane readiness
- `POST /api/public/egregore/register` — update manifest from client profile payload

---

## Transition path

1. **Now:** 4-bit production + BitNet sidecar for specialist tasks  
2. **Next:** Distill Ake behavior into `bitnet-b1.58-2B-4T-bf16` SFT slices  
3. **Later:** Native 1.58-bit Ake if eval gates pass at 7B-class scale  

Related: [MORPHIC_ENSEMBLE_GATEWAY.md](./MORPHIC_ENSEMBLE_GATEWAY.md) · [R730_UNIFIED_MEMORY_PLAN.md](./R730_UNIFIED_MEMORY_PLAN.md)
