#!/usr/bin/env python3
"""Smoke the Deep Key lab thread (same questions as operator UI)."""
import json
import time
import urllib.request

GATEWAY = "http://127.0.0.1:3020/api/lab/unified-lora/chat"


def lab_chat(msg, history=None):
    body = {
        "message": msg,
        "history": history or [],
        "use_ollama": True,
        "use_persona": False,
        "max_tokens": 180,
        "temperature": 0.25,
    }
    req = urllib.request.Request(
        GATEWAY,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read().decode())
    return d, time.time() - t0


def main():
    q1 = "ake, what can you tell me about what is going on here?"
    d1, t1 = lab_chat(q1)
    print(f"Q1 ({t1:.1f}s):", d1.get("content", d1))
    print("---")
    hist = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": d1.get("content", "")},
    ]
    q2 = "and what mission do you have?"
    d2, t2 = lab_chat(q2, hist)
    print(f"Q2 ({t2:.1f}s):", d2.get("content", d2))
    print("---")
    hist.extend(
        [
            {"role": "user", "content": q2},
            {"role": "assistant", "content": d2.get("content", "")},
        ]
    )
    q3 = "what can you tell me about your role in all of it?"
    d3, t3 = lab_chat(q3, hist)
    print(f"Q3 ({t3:.1f}s):", d3.get("content", d3))


if __name__ == "__main__":
    main()
