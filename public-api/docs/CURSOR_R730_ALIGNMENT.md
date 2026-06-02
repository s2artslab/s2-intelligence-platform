# Cursor + r730 alignment runbook

This runbook standardizes how Cursor and local tools should use r730 inference safely and reliably.

## Current topology

- r730 host firewall is intentionally strict (`policy_in: DROP`).
- LAN access from developer machines is allowed for management ports (for example SSH `22`).
- Inference ports (`11434`, `3020`, `8000`, `8100`) are blocked from LAN by default.
- Ollama on r730 is healthy and bound on the host, but should be treated as an internal service.

## Phase 1 - Developer connectivity baseline

Use SSH forwarding instead of direct LAN calls to `192.168.1.78:11434`.

### One command (recommended)

```powershell
cd c:\Users\shast\S2\APPs\s2-intelligence-platform\public-api
.\scripts\start-r730-inference-tunnel.ps1
```

This creates:

- `http://127.0.0.1:3020` -> r730 gateway `:3020`
- `http://127.0.0.1:11434` -> r730 Ollama `:11434`
- `http://127.0.0.1:8120` -> r730 BitNet sidecar `:8120` (research lane)

### Quick verification

```powershell
.\scripts\verify-r730-inference-tunnel.ps1
curl.exe http://127.0.0.1:11434/api/tags
curl.exe http://127.0.0.1:3020/health
curl.exe http://127.0.0.1:8120/health
curl.exe http://127.0.0.1:3020/api/research/bitnet/status
```

BitNet deploy on r730 (when on LAN/VPN):

```powershell
.\scripts\deploy-bitnet-lane-r730.ps1          # stub sidecar (fast)
.\scripts\deploy-bitnet-lane-r730.ps1 -FullModel  # download GGUF
```

## Phase 2 - Network policy decision

Preferred policy is to keep r730 inference ports closed on LAN and use:

- SSH tunnels for local development
- Cloudflare tunnel when remote/public access is needed

Avoid opening `11434` directly on LAN unless you explicitly want broad local network reachability.

## Phase 3 - Inference routing standard

Use these defaults:

- Server-side (`public-api` on r730): `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- Client-side local dev from workstation: `http://127.0.0.1:11434` through SSH tunnel
- Production app traffic: call gateway/API host, not raw Ollama

## Phase 4 - Cursor integration

In Cursor settings:

- OpenAI-compatible Base URL: `http://127.0.0.1:11434/v1`
- API key: any non-empty value (for example `ollama`)
- Model: `s2-ake:latest` (or another installed model)

Important: Cursor cloud Agent limits are still separate from your local inference usage.

## Phase 5 - Operational fallback stack

When Cursor cloud rate limits are hit:

1. Keep coding via Cursor chat using local Ollama tunnel.
2. Route product testing through local gateway tunnel (`:3020`).
3. Use BYOK providers (for example Groq) when a higher-capacity cloud model is needed.

## Phase 6 - Team hygiene

- Do not hardcode `http://192.168.1.78:11434` in new client defaults.
- Prefer localhost tunnel URLs in dev examples.
- Keep one canonical tunnel script and reference it in docs.

## Scripts (canonical)

| Script | Purpose |
|--------|---------|
| `scripts/start-r730-inference-tunnel.ps1` | Forward `:3020` + `:11434` + `:8120` from r730 |
| `scripts/verify-r730-inference-tunnel.ps1` | Health check through local forwards |
| `scripts/deploy-bitnet-lane-r730.ps1` | Sync + deploy BitNet experimental lane |
| `scripts/smoke-bitnet-local.ps1` | Local sidecar + gateway smoke (no r730) |
| `scripts/r730-pull-cursor-coder-models.sh` | On r730: pull `qwen2.5-coder:7b` |
| `scripts/r730-apply-ollama-cursor-env.sh` | On r730: Ollama CORS + longer keep-alive |

## Phase 3 (GPU) - r730 operator steps

On r730 (SSH):

```bash
cd /path/to/s2-intelligence-platform/public-api
bash scripts/r730-apply-ollama-cursor-env.sh
bash scripts/r730-pull-cursor-coder-models.sh
```

Confirm GPU use during inference:

```bash
nvidia-smi
ollama run qwen2.5-coder:7b "write a hello world in python"
```

## Phase 2 (remote Cursor) - Cloudflare quick tunnel

When Cursor cannot reach your LAN (cloud backend path), expose Ollama temporarily:

```powershell
cloudflared tunnel --url http://127.0.0.1:11434 --http-host-header localhost:11434
```

Use the printed `https://*.trycloudflare.com/v1` URL in Cursor **Override OpenAI Base URL**.

## Daily workflow checklist

1. `.\scripts\start-r730-inference-tunnel.ps1`
2. `.\scripts\verify-r730-inference-tunnel.ps1`
3. Cursor: Base URL `http://127.0.0.1:11434/v1`, model `s2-ake:latest` or `qwen2.5-coder:7b`
4. App dev: `S2_API_URL=http://127.0.0.1:3020`
5. Reserve Cursor cloud Agent for hard tasks; use local chat for volume work
