# Layer 2 — Discourse (topology)

**Job:** Mind-shape — how argument, pivot, disagreement, and recursion actually move.

## Is

- Real Ninefold / deep key / legal / strategic threads (consent-tagged)
- Multi-turn structure preserved: interruptions, uncertainty, unfinished arcs
- Training material for **discourse grammar**, not polish

## Is not

- Synthetic `question` → `ake_response` harmony rows
- Flattened assistant-only transcripts

## Schema

[s2-research/discourse/schemas/discourse-thread.schema.json](../../../../s2-research/discourse/schemas/discourse-thread.schema.json)

## Pipeline (planned)

1. Export approved threads → JSONL
2. Tag `cadence`, `tension_ids`, `consent_scope`
3. SFT on full thread text (loss on participant labels per policy)
4. Exclude from foundation blend unless explicitly intended

## Owner

Research ingests; r730 training consumes exported bundles.
