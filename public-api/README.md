# S² Intelligence Public API

Thin Node server for **Pro Se Legal** and other S² clients. Runs on port **3010** by default.

## Bring your own Groq (BYOK)

Clients send the user's Groq API key on each request:

```http
X-Groq-Api-Key: gsk_...
```

The server builds egregore/legal system prompts and calls **Groq** with that key. S² does not store user keys.

Optional lab fallback: set `GROQ_API_KEY` in the environment (single-tenant dev only).

## Run

```bash
cd public-api
npm install
npm start
```

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| GET | `/api/public/capability` | Client capability probe |
| POST | `/api/ai/chat` | Canonical chat (`text`, `egregore_id`, `context`) |
| POST | `/api/public/chat-with-context` | Thin client (`user_message`, `history`, `egregore`) |
| POST | `/api/public/chat` | OpenAI-style `messages[]` |

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3010` | Listen port |
| `GROQ_API_KEY` | — | Optional server key (lab) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Groq model id |
| `CORS_ORIGIN` | `*` | CORS allowed origin |
