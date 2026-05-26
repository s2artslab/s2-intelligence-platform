#!/usr/bin/env python3
import json
import urllib.request

BASE = "http://127.0.0.1:8100"


def gen(payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


print("=== direct :8100 (tier A defaults) ===")
out = gen(
    {
        "egregore": "ake",
        "prompt": "Say hello in one short sentence.",
        "use_persona": False,
        "max_length": 80,
        "do_sample": False,
    }
)
print("meta:", out.get("meta"))
print("response:", (out.get("response") or "")[:400])

print("\n=== gateway hosted ===")
body = json.dumps({"text": "Say hello in one short sentence.", "context": "general"}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:3020/api/public/chat",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-S2-Inference": "hosted",
        "X-Owner-Id": "lab-test",
    },
    method="POST",
)
with urllib.request.urlopen(req, timeout=300) as r:
    d = json.loads(r.read())
print("source:", d.get("source"), "model:", d.get("model"))
print("content:", (d.get("content") or "")[:400])
