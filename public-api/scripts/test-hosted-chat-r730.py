#!/usr/bin/env python3
import json
import urllib.request

body = json.dumps(
    {
        "text": "In one sentence, what is a motion to dismiss?",
        "context": "legal",
    }
).encode()
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
with urllib.request.urlopen(req, timeout=200) as resp:
    print(resp.status)
    print(resp.read().decode()[:1200])
