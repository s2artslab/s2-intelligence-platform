#!/usr/bin/env python3
import json, urllib.request
body = json.dumps({"text": "Say hello in one sentence.", "context": "general"}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:3020/api/public/chat",
    data=body,
    headers={"Content-Type": "application/json", "X-S2-Inference": "hosted", "X-Owner-Id": "lab-test"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=120) as r:
    d = json.loads(r.read())
print("source:", d.get("source"))
print("model:", d.get("model"))
print("content:", (d.get("content") or "")[:200])
