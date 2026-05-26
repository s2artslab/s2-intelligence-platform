# Collective knowledge (RAG corpus)

Files here are loaded at API startup into an in-memory index (`lib/rag.js`).

## Formats

- **Markdown** (`.md`) — split on `##` headings; each section becomes a chunk.
- **JSON** (`.json`) — `{ "chunks": [{ "id", "text", "tags": [] }] }`.

## Adding content

1. Add or edit files in this directory.
2. Restart `public-api` (or redeploy).
3. Confirm `GET /api/public/capability` shows `rag_available: true`.

Keep chunks factual and app-safe. Do not put user PII or secrets here.

## Tags

Use `tags` in JSON chunks to boost retrieval (e.g. `legal`, `billing`, `hosted`).
