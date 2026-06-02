#!/usr/bin/env python3
"""Side-by-side: unified LoRA (:8100) vs Ollama s2-ake on the same prompts."""
from __future__ import annotations

import json
import time
import urllib.request

PROMPTS = [
    "Say hello in one short sentence.",
    "What is a motion to dismiss?",
    "Explain qualified immunity in plain language.",
    "How should a pro se litigant respond to a Rule 12(b)(6) motion?",
]

DEBRIS = [
    "In the context of",
    "From a legal perspective",
    "From a synthesis perspective",
    "art of integration",
]


def post(url: str, body: dict, timeout: int = 300) -> tuple[float, dict]:
    req = urllib.request.Request(
        url,
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return time.time() - t0, json.loads(r.read().decode())


def unified(prompt: str) -> tuple[float, str]:
    elapsed, out = post(
        "http://127.0.0.1:8100/generate",
        {
            "egregore": "ake",
            "prompt": prompt,
            "use_persona": False,
            "do_sample": False,
            "max_length": 180,
        },
    )
    return elapsed, (out.get("response") or "").strip()


def ollama(prompt: str) -> tuple[float, str]:
    elapsed, out = post(
        "http://127.0.0.1:11434/api/chat",
        {
            "model": "s2-ake",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.2},
        },
    )
    msg = out.get("message") or {}
    return elapsed, (msg.get("content") or "").strip()


def debris_flags(text: str) -> list[str]:
    low = text[:220].lower()
    return [d for d in DEBRIS if d.lower() in low]


def main() -> int:
    print("=" * 72)
    print("UNIFIED LoRA (v3, 4-bit, training format)  vs  OLLAMA (s2-ake)")
    print("=" * 72)

    lora_times: list[float] = []
    ollama_times: list[float] = []

    for i, p in enumerate(PROMPTS, 1):
        print(f"\n--- [{i}] {p} ---")
        try:
            tu, u = unified(p)
            lora_times.append(tu)
        except Exception as e:
            tu, u = 0.0, f"ERROR: {e}"
        try:
            to, o = ollama(p)
            ollama_times.append(to)
        except Exception as e:
            to, o = 0.0, f"ERROR: {e}"

        print(f"  LoRA   {tu:5.1f}s  debris={debris_flags(u) or 'none'}")
        print(f"         {u[:300]}{'...' if len(u) > 300 else ''}")
        print(f"  Ollama {to:5.1f}s  debris={debris_flags(o) or 'none'}")
        print(f"         {o[:300]}{'...' if len(o) > 300 else ''}")

    if lora_times and ollama_times:
        print("\n" + "=" * 72)
        print(
            f"Avg latency: LoRA {sum(lora_times)/len(lora_times):.1f}s  |  "
            f"Ollama {sum(ollama_times)/len(ollama_times):.1f}s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
