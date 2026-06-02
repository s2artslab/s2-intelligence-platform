# Governed interface — operators

**Audience:** r730 operators, gateway maintainers  
**Research hub:** [s2-research/docs/governed-interface/README.md](../../../s2-research/docs/governed-interface/README.md)  
**Marketing:** [s2-marketing/docs/AKE_MESSAGING_CONTINUITY.md](../../../s2-marketing/docs/AKE_MESSAGING_CONTINUITY.md)

---

## Definition

The **governed interface** is the hosted product boundary (`:3020` gateway) where:

1. A single assistant identity is assembled (`lib/prompts.js`).
2. Inference routes to Ollama `s2-ake` by default, unified LoRA after Tier C gate, or **BitNet compact lane** for specialist tasks when `BITNET_ENABLED=true`.
3. RAG and billing apply before compute.
4. Audit fields can be logged per [governed-interface-audit.schema.json](../../../s2-research/docs/governed-interface/schemas/governed-interface-audit.schema.json).

---

## Production checklist

| Check | Command / doc |
|-------|----------------|
| Gateway health | `curl -s http://127.0.0.1:3020/health` |
| BitNet sidecar | `curl -s http://127.0.0.1:8120/health` |
| BitNet research API | `curl -s http://127.0.0.1:3020/api/research/bitnet/status` |
| BitNet deploy | `bash scripts/deploy-bitnet-lane-r730.sh` · [BITNET_EXPERIMENTAL_LANE.md](./BITNET_EXPERIMENTAL_LANE.md) |
| BitNet benchmark | `python3 scripts/bitnet-benchmark-r730.py` |
| BitNet eval gate | `python3 scripts/bitnet-eval-gate-r730.py` |
| LoRA status | [AKE_LORA_STATUS.md](./AKE_LORA_STATUS.md) |
| `HOSTED_PREFER_UNIFIED_LORA` | Must be `false` until Tier C gate exits 0 |
| Tier C retrain | [TIER_C_RETRAIN_RUNBOOK.md](./TIER_C_RETRAIN_RUNBOOK.md) |
| Eval gate | `python3 scripts/tier-c-eval-gate-r730.py` |
| Rollback to Ollama | `scripts/r730-force-ollama-env.py` |

---

## Do not

- Point consumer apps at Ollama directly when `USE_HOSTED_GATEWAY=true`.
- Enable `HOSTED_PREFER_UNIFIED_LORA=true` without eval gate pass.
- Merge BIPRA GPT-2 checkpoints into Llama Ollama ([LORA_TO_OLLAMA.md](./LORA_TO_OLLAMA.md)).

---

## Related index

[public-api/docs/README.md](./README.md)
