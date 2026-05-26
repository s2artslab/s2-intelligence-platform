# Tier A/B inference results (r730, May 2026)

## Changes deployed

### Tier A (`:8100` + gateway)

| Setting | Value |
|---------|--------|
| `EGREGORE_USE_PERSONA` | `0` — training format only (`User:` / `Ake:`) |
| `EGREGORE_DO_SAMPLE` | `0` — greedy decoding |
| `EGREGORE_DEFAULT_TEMPERATURE` | `0.2` |
| `EGREGORE_MAX_NEW_TOKENS` | `150` |
| Response trim | First `\n\n` block only |

### Tier B (adapter load)

| Mode | Behavior |
|------|----------|
| `egregore_only` (default) | `PeftModel.from_pretrained(base, ake)` — matches training `set_adapter(ake)` |
| `merge_foundation` | Merge `s2_foundation` into base, then load `ake` |
| `foundation_merged` | Foundation only (ablation) |

### Gateway (`lib/unified-lora.js`)

- `UNIFIED_USE_PERSONA=0`, `UNIFIED_MAX_TOKENS=150`, `UNIFIED_TEMPERATURE=0.2`
- System + RAG embedded into the **user** turn (unified has no system role)

## Ablation smoke (3 questions × modes)

| Mode | Sample output |
|------|----------------|
| `egregore_only` + Tier A | Short prompts: odd `2: Hello, world!`; **training Q**: coherent synthesis answer |
| `merge_foundation` + Tier A | Worse — architecture/list debris |
| Training-format Q (row 0) | **Readable**: "From a synthesis perspective, finding connections requires…" (foundation phrasing, not "In my view") |
| Gateway hosted | Uses unified when warm; Ollama fallback if unified times out during load |

## Conclusions

1. **Tier A fixes distribution and decoding** but cannot fix a weak or misaligned LoRA alone.
2. **`egregore_only` is the correct load graph** vs `merge_foundation` for this training run.
3. **Hosted users get better text from Ollama today** when unified is loading or returns poor LoRA output; health may show `unified_lora.ok: false` while the 7B model loads (~30s+).
4. **Tier C (retrain)** still required: label masking on `Ake:` tokens only, production prompt in training, eval gate before `HOSTED_PREFER_UNIFIED_LORA=true`. Runbook: [TIER_C_RETRAIN_RUNBOOK.md](./TIER_C_RETRAIN_RUNBOOK.md) · gate: `scripts/tier-c-eval-gate-r730.py` · status: [AKE_LORA_STATUS.md](./AKE_LORA_STATUS.md).

## Systemd drop-ins

- `/etc/systemd/system/unified-egregore.service.d/7b-cuda.conf`
- `/etc/systemd/system/unified-egregore.service.d/tier-ab.conf`

## Scripts (repo)

- `scripts/r730-tier-ab-patch-app.py`
- `scripts/tier-ab-ablation-r730.py`
- `scripts/r730-quick-tier-ab-smoke.py`
- `scripts/setup-unified-7b-r730.sh`
