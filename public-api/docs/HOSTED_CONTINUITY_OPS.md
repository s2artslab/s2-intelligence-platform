# Hosted continuity — operator notes

After deploy/sync to r730:

```bash
cd /opt/s2-ecosystem/public-api
npm run build:retrieval-index
# restart gateway
systemctl restart s2-public-api   # or your unit name
```

Verify:

```bash
curl -s http://127.0.0.1:3020/health | jq '.canon,.memory,.rag'
```

Memory routes (optional `MEMORY_API_KEY`):

- `GET /api/public/memory/tensions` — header `X-Owner-Id`
- `POST /api/public/memory/tensions` — body `{ "statement": "...", "status": "open" }`
- `POST /api/internal/continuity/reload` — reload canon + retrieval index

Chat responses include `cadence`, `canon_used`, `tensions_active`.
