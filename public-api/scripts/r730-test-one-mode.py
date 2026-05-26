#!/usr/bin/env python3
import json
import os
import sys
import urllib.request

mode = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("EGREGORE_ADAPTER_LOAD_MODE", "merge_foundation")
body = json.dumps(
    {
        "egregore": "ake",
        "prompt": "Say hello in one sentence.",
        "use_persona": False,
        "max_length": 60,
        "do_sample": False,
    }
).encode()
req = urllib.request.Request(
    "http://127.0.0.1:8100/generate",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=300) as r:
    d = json.loads(r.read())
print("mode_env", mode)
print("meta", d.get("meta"))
print("response", (d.get("response") or "")[:400])
