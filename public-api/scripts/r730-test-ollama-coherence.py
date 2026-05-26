#!/usr/bin/env python3
import json
import time
import urllib.request


def ollama(prompt, max_tokens=150):
    body = json.dumps(
        {
            "model": "s2-ake",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.35, "num_predict": max_tokens},
        }
    ).encode()
    t0 = time.time()
    r = urllib.request.urlopen(
        urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        ),
        timeout=120,
    )
    d = json.loads(r.read())
    return time.time() - t0, d.get("message", {}).get("content", "")


def gateway(text, ctx="general"):
    body = json.dumps({"text": text, "context": ctx}).encode()
    t0 = time.time()
    r = urllib.request.urlopen(
        urllib.request.Request(
            "http://127.0.0.1:3020/api/public/chat",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-S2-Inference": "hosted",
                "X-Owner-Id": "lab-test",
            },
            method="POST",
        ),
        timeout=120,
    )
    d = json.loads(r.read())
    return time.time() - t0, d.get("source"), d.get("content", "")


def show(tag, dt, text, src=None):
    one = " ".join(text.split())[:220]
    prefix = f"[{tag}] {dt:.1f}s"
    if src:
        prefix += f" src={src}"
    print(f"{prefix}\n  {one}\n")


prompts = [
    ("hello", "Say hello in one sentence.", "general"),
    ("legal", "In one sentence, what is a motion to dismiss?", "legal"),
    ("math", "What is 2+2? Reply with just the number and one word of explanation.", "general"),
    (
        "deadlines",
        "Explain in 3 bullet points how pro se litigants should check court deadlines.",
        "legal",
    ),
]

print("=== Ollama direct (no gateway system prompt) ===")
for tag, p, _ctx in prompts:
    dt, txt = ollama(p)
    show(tag, dt, txt)

print("=== Gateway hosted (full Ake system + RAG) ===")
for tag, p, ctx in prompts:
    dt, src, txt = gateway(p, ctx)
    show(tag, dt, txt, src)
