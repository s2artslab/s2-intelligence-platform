# Tier C retrain runbook — Ake LoRA (7B)

**Goal:** Close train/serve gap so unified LoRA is safe for hosted users.

**Prerequisites:** Tier A/B inference patches already on r730 ([TIER_AB_RESULTS.md](./TIER_AB_RESULTS.md)). BIPRA mounted at `/mnt/bipra`.

**Do not** enable `HOSTED_PREFER_UNIFIED_LORA=true` until the eval gate in §5 passes.

---

## 1. What Tier C fixes

| Problem (Tier A/B ablation) | Tier C fix |
|----------------------------|------------|
| Incoherent short prompts | Train on production-shaped turns, not only bare Q/A |
| Model echoes `User:` / prompt structure | **Label masking** — loss on `Ake:` completion tokens only |
| “Foundation phrasing” on easy items | Production system block in training data |
| Hosted worse than Ollama | Eval gate vs `s2-ake` before flipping gateway preference |

---

## 2. Dataset format (v2)

### 2.1 Minimum fields per example

```json
{
  "id": "ake-legal-0001",
  "context": "legal",
  "jurisdiction": "N.D. Cal.",
  "system": "<AKE_CORE + LEGAL_OVERLAY — same text as lib/prompts.js>",
  "user": "What is a motion to dismiss?",
  "assistant": "A motion to dismiss asks the court to end the case early because..."
}
```

Export gateway-aligned system text from repo:

```bash
cd APPs/s2-intelligence-platform/public-api
python3 scripts/export-tier-c-dataset-template.py --out training_data/ake_tier_c_v2_template.jsonl
```

Copy merged JSONL to r730: `/opt/s2-ecosystem/egregore-training/training_data/ake_tier_c_v2.jsonl`

### 2.2 Serialize to training string (unified `:8100` format)

For each row, build one sample:

```text
{system_block}

---
User question:
{user}

Ake: {assistant}
```

Rules:

- Use literal prefixes `User question:` and `Ake:` (matches [unified-lora.js](../lib/unified-lora.js) embedding).
- Include **RAG block** in `system` for ~30% of legal rows (same `--- REFERENCE MATERIAL ---` wrapper as gateway).
- Mix **short** user questions (≤120 chars) and **long** matter-context questions.
- Hold out 10% for eval gate (never train on holdout ids).

### 2.3 Negative examples to filter

Drop rows where `assistant` contains:

- `2: Hello, world!`
- `architecture`, `list debris`, multiple numbered fake sections
- Role-play of other egregores

---

## 3. Label masking (required)

**Loss applies only to tokens after `Ake:`** (the assistant completion). Mask `User:`, system, separators, and the `Ake:` prefix with `-100`.

Reference collator (copy to r730 training tree):

```bash
cp public-api/scripts/tier-c-label-mask-collator.py \
  /opt/s2-ecosystem/egregore-training/scripts/tier_c_label_mask_collator.py
```

Integration in existing trainer (pseudocode):

```python
from tier_c_label_mask_collator import TierCLabelMaskCollator

collator = TierCLabelMaskCollator(
    tokenizer=tokenizer,
    response_prefix="Ake:",
    max_length=2048,
)
trainer = Trainer(..., data_collator=collator)
```

**Do not** use `DataCollatorForLanguageModeling` without masking for Tier C — that trains on the full sequence and reproduces prompt echo.

---

## 4. Training run (7B on r730)

Base script (on r730, paths may vary):

```bash
cd /opt/s2-ecosystem/egregore-training
# Use your 7B foundation + ake adapter script, e.g.:
# python train_egregore_on_foundation_7b.py \
#   --dataset training_data/ake_tier_c_v2.jsonl \
#   --egregore ake \
#   --output-dir /mnt/bipra/egregore-training/trained_models/ake_tier_c_v2 \
#   --collator scripts/tier_c_label_mask_collator.py
```

Hyperparameters (starting point — tune from Tier B checkpoint):

| Param | Value |
|-------|--------|
| Epochs | 2–3 |
| LR | 1e-4 → 5e-5 (adapter only) |
| Batch | Max that fits P40 with grad checkpointing |
| `EGREGORE_ADAPTER_LOAD_MODE` | `egregore_only` |

After export, point unified service:

```bash
export ADAPTERS_BASE=/mnt/bipra/egregore-training/trained_models
# Ensure ake adapter path contains new weights
bash /opt/s2-ecosystem/public-api/scripts/setup-unified-production-r730.sh
```

---

## 5. Eval gate (must exit 0)

On r730:

```bash
python3 /opt/s2-ecosystem/public-api/scripts/tier-c-eval-gate-r730.py \
  --unified-url http://127.0.0.1:8100 \
  --ollama-url http://127.0.0.1:11434 \
  --model s2-ake
```

Gate checks:

1. **Short prompts** (3): no debris patterns; min length; on-topic
2. **Training-format** (3): coherent synthesis-style answer
3. **Gateway smoke** (1): `POST :3020` legal question returns substantive text
4. **Optional:** unified not worse than Ollama on short set (heuristic length + keyword sanity)

Only then:

```bash
sed -i 's/^HOSTED_PREFER_UNIFIED_LORA=.*/HOSTED_PREFER_UNIFIED_LORA=true/' \
  /opt/s2-ecosystem/public-api/.env
systemctl restart s2-public-api
```

---

## 6. Optional — Ollama `s2-ake-lora`

After 7B adapter is stable on `:8100`:

1. [LORA_TO_OLLAMA.md](./LORA_TO_OLLAMA.md) — merge or ADAPTER path
2. Keep `HOSTED_PREFER_UNIFIED_LORA` as primary unless Ollama merge quality exceeds unified in A/B
3. `OLLAMA_PREFER_LORA=true` only when `ollama list` shows `s2-ake-lora` and smoke passes

---

## 7. Rollback

```bash
bash /opt/s2-ecosystem/public-api/scripts/setup-unified-production-r730.sh
python3 /opt/s2-ecosystem/public-api/scripts/r730-force-ollama-env.py
systemctl restart s2-public-api unified-egregore
```

Hosted users immediately return to Ollama-only path.

---

## 8. Checklist

- [ ] v2 JSONL with production system blocks + short/long mix
- [ ] Label masking collator wired
- [ ] 7B train complete; weights under `/mnt/bipra/.../trained_models/ake`
- [ ] `tier-c-eval-gate-r730.py` exit 0
- [ ] `test-hosted-chat-r730.py` substantive
- [ ] `HOSTED_PREFER_UNIFIED_LORA=true` only after above
- [ ] [AKE_LORA_STATUS.md](./AKE_LORA_STATUS.md) updated with date + checkpoint id
