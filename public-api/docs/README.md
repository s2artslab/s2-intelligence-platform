# public-api docs index



| Doc | When to read |

|-----|----------------|

| [GOVERNED_INTERFACE.md](./GOVERNED_INTERFACE.md) | **Ops entry** — gateway boundary, checklist, links to research hub |

| [AKE_CONTINUITY_ARCHITECTURE.md](./AKE_CONTINUITY_ARCHITECTURE.md) | **Start here (continuity)** — six layers, build order, monolith split |
| [AKE_CONTINUITY_IMPLEMENTATION.md](./AKE_CONTINUITY_IMPLEMENTATION.md) | Phase 0–3 checklist, env vars |
| [HOSTED_CONTINUITY_OPS.md](./HOSTED_CONTINUITY_OPS.md) | r730 deploy + memory API |

| [layers/](./layers/) | Per-layer specs (canon → asymmetry) |

| [AKE_IDENTITY_AND_TRAINING_ARCHITECTURE.md](./AKE_IDENTITY_AND_TRAINING_ARCHITECTURE.md) | Legacy pipeline — archetype vs synthetic rows vs weights |

| [AKE_LORA_STATUS.md](./AKE_LORA_STATUS.md) | Production vs lab, stack split, gates |

| [HOSTED_AKE_GATEWAY.md](../HOSTED_AKE_GATEWAY.md) | Gateway architecture and r730 deploy |

| [TIER_C_RETRAIN_RUNBOOK.md](./TIER_C_RETRAIN_RUNBOOK.md) | Retrain with label masking + eval gate |

| [TIER_AB_RESULTS.md](./TIER_AB_RESULTS.md) | May 2026 ablation |

| [R730_UNIFIED_MEMORY_PLAN.md](./R730_UNIFIED_MEMORY_PLAN.md) | P40 GPU memory (hardware), not Layer 4 identity memory |

| [DEPLOY_TRAINED_LORA.md](./DEPLOY_TRAINED_LORA.md) | Post-training `:8100` + `:3020` |

| [LORA_TO_OLLAMA.md](./LORA_TO_OLLAMA.md) | Optional `s2-ake-lora` after 7B weights |



**Research:** [s2-research/docs/governed-interface/](../../../s2-research/docs/governed-interface/README.md) · [ake-continuity/](../../../s2-research/docs/ake-continuity/README.md) · **Marketing:** [s2-marketing/docs/AKE_MESSAGING_CONTINUITY.md](../../../s2-marketing/docs/AKE_MESSAGING_CONTINUITY.md)



**Scripts:** `scripts/tier-c-eval-gate-r730.py` · `scripts/setup-unified-production-r730.sh` · `scripts/export-tier-c-dataset-template.py`

