# Morphic resonance & PSLA ensemble — gateway spec

**Status:** May 2026 (inference profiles + morphic bias; ensemble opt-in + cheap collapse)  
**Claims:** Public “1.58 dimensions” = **M**. `MORPHIC_RESONANCE` = **O** (user bias dial). `inference_profile` axes = **O**.

---

## Production default

| Layer | Default | Cost |
|-------|---------|------|
| **Inference profile** | Task-detected (legal, philosophy, coding, …) | **1** inference — decoupled temp / RAG / depth |
| **Morphic interval** | ON (`MORPHIC_RESONANCE=1.58`) | User bias on profile axes (efficiency ↔ ability) |
| **Ensemble collapse** | **OFF** | Opt in per request |

Public UX stays one dial (`morphic_resonance`). Internal mapping uses **three axes + depth**:

| Axis | Controls |
|------|----------|
| **Precision** | Temperature, product-temp blend weight |
| **Context** | RAG chunk count, RAG max chars |
| **Synthesis** | Small temperature nudge (cadence overlay handles register) |
| **Depth** | `max_tokens` multiplier when client omits explicit budget |

---

## Task profiles (internal)

| Profile | Precision | Context | Synthesis | Depth | Typical morphic |
|---------|-----------|---------|-----------|-------|-------------------|
| **legal** | 95 | 90 | 30 | 65 | 1.58 |
| **coding / debug** | 75 | 85 | 50 | 80 | 1.59 |
| **strategy / exploration** | 65 | 70 | 70 | 75 | 1.60 |
| **philosophy** | 70 | 55 | 95 | 85 | 1.61 |
| **creativity** | 55 | 45 | 95 | 70 | 1.618 |

Legal at 1.58 now gets **cold sampling + deep retrieval** (previously coupled low on both).

---

## Lab / power-user override

Optional per-request axes (0–100). Partial overrides merge with the detected profile:

```json
POST /api/public/chat
{
  "text": "Rule 12(b)(6) options",
  "context": "legal",
  "inference_profile": {
    "precision": 95,
    "context": 90,
    "synthesis": 30,
    "depth": 65
  }
}
```

Public dial still accepted:

```json
{ "morphic_resonance": 1.618 }
```

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
MORPHIC_RAG_LIMIT_MAX=12
MORPHIC_RAG_CHARS_MAX=4800
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
  "morphic_resonance": 1.58,
  "morphic_label": "grounded",
  "morphic_rag_limit": 11,
  "inference_profile": {
    "precision": 96,
    "context": 88,
    "synthesis": 28,
    "depth": 64
  },
  "inference_profile_key": "legal",
  "inference_source": "profile:legal",
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
| `lib/morphic-dimension.js` | Public 1.58–1.618 dial |
| `lib/inference-profile.js` | Task profiles → decoupled knobs |
| `lib/morphic-resonance.js` | Backward-compat `resolveMorphicPolicy` |
| `lib/ensemble-collapse.js` | Opt-in, cheap vs full |
| `lib/consciousness-metrics.js` | `/api/consciousness/status` |
