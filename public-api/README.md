# S² Intelligence Public API

Ake gateway for **Pro Se Legal** and other S² apps. Port **3010** by default.

## Product model

- **One assistant** in the UI (S² Assistant).
- **Hosted** ($29/mo): private Ollama `s2-ake` + collective RAG + templates.
- **BYOK**: user Groq key, same server-side assembly.

See [HOSTED_AKE_GATEWAY.md](./HOSTED_AKE_GATEWAY.md) for architecture and deploy.

**Operator status (LoRA / Ollama / Tier C):** [docs/AKE_LORA_STATUS.md](./docs/AKE_LORA_STATUS.md)

## Quick start

```bash
cd public-api
cp .env.example .env
npm install
npm start
```

Create the Ollama model (on the GPU host):

```powershell
.\scripts\create-s2-ake-model.ps1
```

## Inference modes

| Mode | Client headers | Server |
|------|----------------|--------|
| Hosted | `X-S2-Inference: hosted`, `X-Owner-Id` | Billing → RAG → **Ollama `s2-ake`** (unified LoRA after Tier C gate) |
| BYOK | `X-Groq-Api-Key` | RAG → Groq |

If neither Groq key nor hosted mode applies, capability endpoint explains what is missing.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Ollama + RAG status |
| GET | `/api/public/capability` | Client probe |
| POST | `/api/ai/chat` | Chat (`text` or `messages`, `context`) |
| POST | `/api/public/chat-with-context` | Thin chat + history |
| POST | `/api/public/chat` | OpenAI-style `messages[]` |
| POST | `/api/psla/exploration/paths` | PSLA pre-filing — structured litigation paths (JSON) |
| POST | `/api/psla/exploration/chat` | PSLA pre-filing chat (`psla-exploration` prompts) |
| POST | `/api/psla/exploration/material-digest` | Summarize long exploration materials |
| POST | `/api/public/document-intelligence/process-pdf` | PDF proxy for web clients (`content_base64`) |
| GET | `/api/public/document-intelligence/health` | Doc-intel tunnel health |

## Thin client body

```json
{
  "user_message": "What is a motion to dismiss?",
  "context": "legal",
  "jurisdiction": "N.D. Cal.",
  "case_context": "Pro se breach of contract…",
  "history": [],
  "rag_limit": 5
}
```

Legacy fields `egregore_id` / `egregore` are ignored for assembly (always Ake).

## Environment

Copy [.env.example](./.env.example). Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3010` | Listen port |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | r730 Ollama |
| `OLLAMA_MODEL` | `s2-ake` | Hosted model name |
| `HOSTED_REQUIRE_BILLING` | `false` | Set `true` in production |
| `LAB_HOSTED_UNLOCK` | — | `true` skips billing (dev) |
| `BILLING_API_URL` | — | S² billing worker |
| `GROQ_API_KEY` | — | Lab BYOK fallback only |
| `S2_KNOWLEDGE_DIR` | `./knowledge` | RAG corpus |

## LoRA model (`s2-ake-lora`)

After training, attach LoRA to Ollama (adapter or merged GGUF): **[docs/LORA_TO_OLLAMA.md](./docs/LORA_TO_OLLAMA.md)**.

With `OLLAMA_PREFER_LORA=true`, the gateway uses `s2-ake-lora` when `ollama list` includes it; otherwise `s2-ake`.

## Collective knowledge (RAG)

Add files under `knowledge/`:

- `*.md` — split on `##` headings into chunks
- `*.json` — `{ "chunks": [{ "id", "text", "tags" }] }`

Restart the API to reload (or redeploy). No vector DB required for MVP.

## Module layout

```
lib/
  prompts.js    # Ake core + legal/general overlays
  ollama.js     # Hosted inference
  groq.js       # BYOK inference
  rag.js        # Collective knowledge retrieval
  billing.js    # Hosted entitlement
server.js       # Express gateway
```

## PSLA integration

PSLA sets `USE_HOSTED_GATEWAY=true` and points `S2_API_URL` at this service.  
See `APPs/pro-se-legal/docs/HOSTED_S2_ASSISTANT.md`.
