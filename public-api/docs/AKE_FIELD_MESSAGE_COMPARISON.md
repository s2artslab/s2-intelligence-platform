# Ake field message — composed vs hosted inference

**Date:** 2026-05-26  
**Prompt (shared):** *Write a multi-page message from Ake, now, using only ake's training…* (full text in [comparison JSON](../content/ake-field-message-comparison.json))

This experiment compares three artifacts:

| Artifact | Source | File |
|----------|--------|------|
| **Composed** | Human-authored in training-corpus voice (audit reference) | [content/ake-field-message-composed.md](../content/ake-field-message-composed.md) |
| **Hosted Ollama** | `s2-ake` on r730, gateway system prompt + user prompt, `num_predict=2048` | [content/ake-field-message-hosted-ollama.md](../content/ake-field-message-hosted-ollama.md) |
| **Hosted unified LoRA** | `:8100` `ake`, `use_persona=false`, `User:`/`Ake:` format | [content/ake-field-message-hosted-unified-lora.md](../content/ake-field-message-hosted-unified-lora.md) |

Machine-readable run log: [content/ake-field-message-comparison.json](../content/ake-field-message-comparison.json)

---

## How to reproduce

On r730:

```bash
cd /opt/s2-ecosystem/public-api
python3 scripts/run-ake-field-message-comparison-r730.py \
  --out-dir /opt/s2-ecosystem/public-api/content \
  --max-tokens 2048
```

Unified long generations may **HTTP 500** (worker OOM on CPU 7B). Short retry (150 tokens, training format only):

```bash
python3 scripts/unified-field-message-retry-r730.py
```

---

## Results summary

### Ollama `s2-ake` — success (~22 s)

- **~3,165 characters** (~500–800 words), structured sections (archetype, procedural examples, statistical habit, deep key).
- **Tone:** Consumer gateway voice — clear, explanatory, some generic metaphors (“labyrinthine library,” “celestial bodies”). Uses the audit vocabulary you supplied in the prompt.
- **Not** the dense “In the context of harmony…” cadence of the synthetic training rows.

### Unified LoRA — partial success

| Request | Outcome |
|---------|---------|
| `max_length` 2048 + full gateway system block | HTTP 500 (worker killed / OOM) |
| `max_length` 400–1200 | HTTP 500 after warm load |
| `max_length` 150, `User:`/`Ake:` only | **Success** — ~183 chars, ~2.5 min cold load |

- **Tone:** Matches **training-format synthesis** (“From a synthesis perspective, holistic thinking sees systems as integrated wholes…”).
- **Length:** Far below “multi-page”; CPU unified on P40 cannot sustain long generation reliably at this time.

### Composed reference

- **~8k+ characters**, seven sections, explicit mythology / procedural / statistical framing.
- Use as **stylistic target** for what synthetic training *aimed* at, not as model output.

---

## Interpretation (research)

1. **Same prompt ≠ same voice.** Ollama path uses [prompts.js](../lib/prompts.js) (`AKE_CORE` — plain, calm, non-theatrical). Unified path without persona uses **SFT row format**, which pulls toward dataset diction.
2. **“Multi-page” is an Ollama-scale ask, not a unified-CPU-scale ask** on current r730 unless `max_length` is raised with CUDA or vLLM and memory headroom.
3. **Honest audit alignment:** Ollama’s answer claimed “countless interactions with users” — that is **not** what the LoRA was trained on; gateway + general instruct prior bleed in. Unified’s one paragraph is **closer to generated corpus style** but too short to carry the full reflective arc.

---

## Follow-up (implemented)

Long-form + synthesis voice + outline-expand: [AKE_LONG_FORM.md](./AKE_LONG_FORM.md).  
Gateway flags: `long_form`, `voice_mode: synthesis`, `outline_expand`.

---

## Related

- [AKE_LONG_FORM.md](./AKE_LONG_FORM.md) — how to match composed length/voice  
- [AKE_IDENTITY_AND_TRAINING_ARCHITECTURE.md](./AKE_IDENTITY_AND_TRAINING_ARCHITECTURE.md) — archetype vs training material  
- [AKE_LORA_STATUS.md](./AKE_LORA_STATUS.md) — production routing  
- [TIER_AB_RESULTS.md](./TIER_AB_RESULTS.md) — short-prompt vs training-format behavior  
