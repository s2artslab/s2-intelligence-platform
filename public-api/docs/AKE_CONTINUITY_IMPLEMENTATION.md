# Ake continuity — implementation roadmap

**Spec:** [AKE_CONTINUITY_ARCHITECTURE.md](./AKE_CONTINUITY_ARCHITECTURE.md)

## Phase 0

| Task | Status |
|------|--------|
| Document six layers | Done |
| `canon/` tree + seed axiom | Done |
| Discourse + tension + retrieval schemas | Done |
| Freeze synthetic harmony expansion | Manual (ops) |

## Phase 1 (inference)

| Task | Status |
|------|--------|
| `S2_CANON_DIR` → `lib/canon.js` + gateway prompt | Done |
| Annotated retrieval → `lib/retrieval-index.js`, `lib/rag.js` | Done |
| Tension store + reflection → `lib/memory/*` | Done |
| APIs: `/api/public/memory/*`, `/api/internal/continuity/reload` | Done |
| `scripts/build-retrieval-index.js` | Done |
| `scripts/export_canon_manifest.py` (s2-research) | Done |

**Build indexes after canon/discourse changes:**

```bash
# s2-research
python scripts/export_canon_manifest.py
python scripts/build_discourse_index.py

# public-api
npm run build:retrieval-index
```

## Phase 2

| Task | Status |
|------|--------|
| Pilot discourse JSONL | Done (`discourse/export/pilot-deep-key-legal.jsonl`) |
| `knowledge/meta.json` annotations | Done |
| Legal cadence LoRA train | r730 — `train_egregore_on_foundation_7b.py` + legal JSONL export |

## Phase 3

| Task | Status |
|------|--------|
| Cadence router in gateway | Done (`lib/cadence-router.js` → `cadence` in chat response) |
| DPO example preferences | Done (`discourse/preferences/example-dpo-pair.jsonl`) |
| Tier C / unified LoRA promote | Ops — unchanged |

## Env

| Variable | Default |
|----------|---------|
| `S2_CANON_DIR` | `./canon` |
| `S2_DISCOURSE_INDEX` | `./data/discourse-index.json` |
| `S2_RETRIEVAL_INDEX` | `./data/retrieval-index.json` |
| `S2_TENSION_STORE` | `./data/tensions` |
| `S2_REFLECTION_ON_CHAT` | `true` |
| `MEMORY_API_KEY` | optional guard for memory admin routes |

## Chat response fields (new)

- `cadence`, `adapter_hint`, `canon_used`, `tensions_active`
