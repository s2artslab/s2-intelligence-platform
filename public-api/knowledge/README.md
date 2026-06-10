# S² collective knowledge (gateway RAG)

Chunks in this tree feed `lib/retrieval-index.js` → `lib/rag.js` on the public API.

## Layout

| Path | Namespaces |
|------|------------|
| `*.md` / `*.json` (root) | From `meta.json` |
| `products/{app-id}/*.md` | `product:{app-id}`, `s2-canon` |
| `data/private-rag/` | Per-owner / per-matter (not in git) |

## Ingest

```bash
# Publish a pack (Forge CI)
node scripts/publish-forge-knowledge-pack.js --app s2forge --readme ./README.md

# Internal API
curl -X POST http://127.0.0.1:3010/api/internal/knowledge/publish-pack \
  -H "X-API-Key: $KNOWLEDGE_INGEST_KEY" \
  -H "Content-Type: application/json" \
  -d '{"product_id":"allies-and-artists","chunks":[{"text":"..."}]}'
```

## Clients

Send `product_id` and optional `rag_namespaces` on chat requests. Beta apps set `X-S2-Product-Id` via `s2-beta-shell.js`.
