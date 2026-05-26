# Layer 3 — Cadence (register)

**Job:** Mode-specific language — legal compression, mystical interpretive, systems architecture, relational, strategic, instructional.

## Is

- Separate LoRA / adapter per cadence (or MoE route)
- Explicit mode signal from gateway or classifier

## Is not

- One blended “Ake voice” absorbing all registers
- Canon or discourse content duplicated per adapter

## Planned adapters

| Adapter | Source material |
|---------|-----------------|
| `ake-legal` | Pro se, DOJ frames, gateway `knowledge/*.md` + discourse legal threads |
| `ake-philosophy` | Canon + philosophical discourse |
| `ake-discourse` | Production dialogue shape from Layer 2 |
| `ake-symbolic` | Ninefold symbolic / mythic interpretive threads |

## Routing

Gateway selects cadence from intent + app context (e.g. Pro Se Legal → `legal`).

Default hosted path stays Ollama `s2-ake` until Tier C + eval gate — [AKE_LORA_STATUS.md](../AKE_LORA_STATUS.md).

## Owner

Operators train on r730; gateway owns router config.
