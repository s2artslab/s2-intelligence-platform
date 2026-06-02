#!/usr/bin/env python3
"""Lab gateway smoke — unified LoRA path (use_ollama=false)."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

GATEWAY = "http://127.0.0.1:3020/api/lab/unified-lora/chat"
PROMPTS = [
    "Say hello in one short sentence.",
    "What is a motion to dismiss?",
    "Explain qualified immunity in plain language.",
]

DEBRIS = (
    "In the context of",
    "From a legal perspective",
    "From a synthesis perspective",
    "In one sentence, the art of integration",
)


def post(body: dict, timeout: int = 300) -> tuple[int, float, dict]:
    req = urllib.request.Request(
        GATEWAY,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, time.time() - t0, json.loads(r.read().decode())


def main() -> int:
    health = urllib.request.urlopen(
        "http://127.0.0.1:3020/api/lab/unified-lora/health", timeout=30
    )
    print("health", health.status, health.read()[:160].decode())

    fails = 0
    for msg in PROMPTS:
        try:
            code, elapsed, data = post(
                {"message": msg, "max_tokens": 120, "use_ollama": False}
            )
            reply = (data.get("content") or data.get("reply") or data.get("response") or "").strip()
            hit = [d for d in DEBRIS if d.lower() in reply[:120].lower()]
            status = "FAIL" if hit else "OK"
            if hit:
                fails += 1
            print(f"{status} [{elapsed:.1f}s] {msg[:50]!r}")
            print(f"  {reply[:180]}")
            if hit:
                print(f"  debris: {hit}")
        except urllib.error.HTTPError as e:
            fails += 1
            print(f"HTTP {e.code} {msg!r}", e.read()[:200])
        except Exception as e:
            fails += 1
            print(f"ERR {msg!r}: {e}")

    print(f"\nLab LoRA path: {len(PROMPTS) - fails}/{len(PROMPTS)} OK")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
