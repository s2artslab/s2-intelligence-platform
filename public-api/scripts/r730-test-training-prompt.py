#!/usr/bin/env python3
"""Exact training-format prompt from ake_blended_dataset row 0."""
import json
import urllib.request

with open("/opt/s2-ecosystem/egregore-training/training_data/ake_blended_dataset.json") as f:
    row = json.load(f)[0]
prompt = row["question"]
expected = row["ake_response"][:120]
body = json.dumps(
    {
        "egregore": "ake",
        "prompt": prompt,
        "use_persona": False,
        "max_length": 100,
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
print("Q:", prompt)
print("expected:", expected)
print("got:", (d.get("response") or "")[:200])
