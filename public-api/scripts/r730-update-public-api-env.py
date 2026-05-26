#!/usr/bin/env python3
from pathlib import Path

p = Path("/opt/s2-ecosystem/public-api/.env")
updates = {
    "UNIFIED_USE_PERSONA": "0",
    "UNIFIED_DO_SAMPLE": "0",
    "UNIFIED_MAX_TOKENS": "150",
    "UNIFIED_TEMPERATURE": "0.2",
}
lines = p.read_text().splitlines() if p.exists() else []
out, seen = [], set()
for line in lines:
    k = line.split("=", 1)[0] if "=" in line else None
    if k in updates:
        if k not in seen:
            out.append(f"{k}={updates[k]}")
            seen.add(k)
        continue
    out.append(line)
for k, v in updates.items():
    if k not in seen:
        out.append(f"{k}={v}")
p.write_text("\n".join(out) + "\n")
print("updated", p)
