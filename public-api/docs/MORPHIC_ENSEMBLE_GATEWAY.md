# Morphic resonance & PSLA ensemble — gateway spec

**Status:** May 2026 (morphic default; ensemble opt-in + cheap collapse)  
**Claims:** Public “1.58 dimensions” = **M**. `MORPHIC_RESONANCE` = **O**.

---

## Production default

| Layer | Default | Cost |
|-------|---------|------|
| **Morphic interval** | ON (`MORPHIC_RESONANCE=1.58`) | **1** inference — tunes temp + RAG |
| **Ensemble collapse** | **OFF** | Opt in per request |

---

## Opt in to ensemble

Any of:

- JSON: `"ensemble": true`
- JSON: `"ensemble_mode": "cheap"` or `"full"`
- Header: `X-S2-Ensemble: cheap` or `full`

Opt out: `"ensemble": false`

**Lab only** — auto-ensemble all PSLA: `ENSEMBLE_PSLA_COLLAPSE=true`

---

## Ensemble modes

| Mode | Inference calls | General path |
|------|-----------------|--------------|
| **cheap** (default when opted in) | **1** | General-context **RAG text** only — compared to legal answer for disagreement |
| **full** | **2** | Second full LLM on general context (`ensemble_mode: "full"`) |

Cheap collapse still applies Deep Key strategies (legal-primary, tension note, dual-frame on high disagreement vs retrieved general chunks).

---

## Environment (r730)

```env
MORPHIC_RESONANCE=1.58
ENSEMBLE_PSLA_COLLAPSE=false
ENSEMBLE_DEFAULT_MODE=cheap
ENSEMBLE_CHEAP_GENERAL_MAX_CHARS=1200
```

| Variable | Production | Lab |
|----------|------------|-----|
| `ENSEMBLE_PSLA_COLLAPSE` | `false` | `true` optional |
| `ENSEMBLE_DEFAULT_MODE` | `cheap` | `cheap` |
| `ENSEMBLE_DISAGREEMENT_THRESHOLD` | `0.28` | tune |
| `ENSEMBLE_HOLD_THRESHOLD` | `0.42` | tune |

---

## Response fields

```json
{
  "morphic_resonance": 1.5867,
  "morphic_label": "efficiency",
  "ensemble": {
    "mode": "cheap",
    "inference_calls": 1,
    "general_source": "rag",
    "strategy": "collapse_legal_agree",
    "disagreement": 0.31
  }
}
```

Omitted when ensemble not requested.

---

## Client example (PSLA)

```json
POST /api/public/chat
{
  "text": "What are my options before filing?",
  "context": "legal",
  "product_id": "psla-hosted",
  "ensemble": true
}
```

Full dual-LLM (expensive):

```json
{ "ensemble": true, "ensemble_mode": "full" }
```

---

## Smoke

```bash
npm run smoke:morphic
```

---

## Code

| Module | Role |
|--------|------|
| `lib/morphic-resonance.js` | Interval → temp/RAG |
| `lib/ensemble-collapse.js` | Opt-in, cheap vs full |
| `lib/consciousness-metrics.js` | `/api/consciousness/status` |
