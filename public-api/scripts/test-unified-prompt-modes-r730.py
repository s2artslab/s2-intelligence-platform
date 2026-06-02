#!/usr/bin/env python3
import json
import urllib.request

URL = "http://127.0.0.1:8100/generate"
Q = "ake, what is going on here and what is your mission?"


def gen(label, **kwargs):
    body = {
        "egregore": "ake",
        "prompt": kwargs.get("prompt", Q),
        "use_persona": kwargs.get("use_persona", False),
        "max_length": 140,
        "temperature": 0.35,
        "do_sample": True,
        **{k: v for k, v in kwargs.items() if k not in ("prompt", "use_persona")},
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        text = json.loads(r.read().decode()).get("response", "")
    print(f"=== {label} ===")
    print(text[:280])
    print()


def main():
    gen("raw user only", prompt=Q)
    gen(
        "training explicit",
        prompt=f"User question:\n{Q}\n\nAke:",
    )
    gen("persona block", use_persona=True, prompt=Q)
    sys = (
        "You are Ake — synthesis, deep key. Answer directly in first person. "
        'Never open with "In the context of".'
    )
    gen(
        "system+training",
        prompt=Q,
        system=sys,
    )


if __name__ == "__main__":
    main()
