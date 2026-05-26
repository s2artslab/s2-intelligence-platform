#!/usr/bin/env python3
"""Set hosted inference to Ollama-only; dedupe .env keys."""
from pathlib import Path

p = Path("/opt/s2-ecosystem/public-api/.env")
lines = p.read_text().splitlines() if p.exists() else []

# Last-wins dedupe while preserving order of other keys
updates = {
    "HOSTED_PREFER_UNIFIED_LORA": "false",
    "OLLAMA_PREFER_LORA": "false",
    "UNIFIED_USE_PERSONA": "0",
}
seen = set()
out = []
for line in lines:
    if not line.strip() or line.strip().startswith("#"):
        out.append(line)
        continue
    if "=" not in line:
        out.append(line)
        continue
    key = line.split("=", 1)[0].strip()
    if key in updates:
        if key not in seen:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        continue
    out.append(line)
for key, val in updates.items():
    if key not in seen:
        out.append(f"{key}={val}")
p.write_text("\n".join(out) + "\n")
print("env ok:", {k: updates[k] for k in updates})
