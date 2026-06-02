#!/usr/bin/env python3
import json
import urllib.error
import urllib.request

for url in ("http://127.0.0.1:11434/api/tags",):
    try:
        print(url, urllib.request.urlopen(url, timeout=5).status)
    except Exception as e:
        print(url, "FAIL", e)

body = json.dumps({"message": "hi", "use_ollama": True}).encode()
req = urllib.request.Request(
    "http://127.0.0.1:3020/api/lab/unified-lora/chat",
    data=body,
    headers={"Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        print("lab", r.status, r.read()[:400])
except urllib.error.HTTPError as e:
    print("lab HTTP", e.code, e.read()[:400])
