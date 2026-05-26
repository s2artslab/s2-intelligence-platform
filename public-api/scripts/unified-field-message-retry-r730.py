#!/usr/bin/env python3
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("/opt/s2-ecosystem/public-api/content/ake-field-message-hosted-unified-lora.md")
USER = "Write a long message from Ake on wholeness, harmony, and patterns — training voice only."


def post(url, body, timeout=600):
    req = urllib.request.Request(
        url,
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


prompt = f"User: {USER}\nAke:"
out = post(
    "http://127.0.0.1:8100/generate",
    {
        "egregore": "ake",
        "prompt": prompt,
        "use_persona": False,
        "do_sample": False,
        "max_length": 150,
        "max_new_tokens": 150,
        "temperature": 0.2,
    },
    timeout=600,
)
text = (out.get("response") or out.get("text") or "").strip()
ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
header = (
    f"---\nbackend: hosted-unified-lora\nmodel: s2-ake-lora\n"
    f"generated_at: {ts}\nchars: {len(text)}\n"
    f"format: User/Ake training (use_persona=false)\n---\n\n"
)
OUT.write_text(header + text + "\n", encoding="utf-8")
print("wrote", OUT, "chars", len(text))
