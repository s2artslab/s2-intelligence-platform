#!/usr/bin/env python3
"""Apply Ollama coherence env on r730."""
from pathlib import Path

p = Path("/opt/s2-ecosystem/public-api/.env")
updates = {
    "OLLAMA_TEMPERATURE": "0.2",
    "OLLAMA_HOSTED_TEMPERATURE": "0.2",
    "OLLAMA_TOP_P": "0.85",
    "OLLAMA_REPEAT_PENALTY": "1.12",
    "OLLAMA_EXPLORATION_TEMPERATURE": "0.2",
    "UNIFIED_TEMPERATURE": "0.2",
}
lines = p.read_text().splitlines() if p.exists() else []
out, seen = [], set()
for line in lines:
    if not line.strip() or line.strip().startswith("#") or "=" not in line:
        out.append(line)
        continue
    key = line.split("=", 1)[0].strip()
    if key in updates:
        if key not in seen:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        continue
    out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
p.write_text("\n".join(out) + "\n")
print("updated ollama env")
