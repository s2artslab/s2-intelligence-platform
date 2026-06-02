#!/usr/bin/env python3
"""Prompt-mode ablation on fixed legal/general questions."""
from __future__ import annotations

import json
import urllib.request

URL = "http://127.0.0.1:8100/generate"
PROMPTS = [
    "Say hello in one short sentence.",
    "What is a motion to dismiss?",
    "How should a pro se litigant respond to a Rule 12(b)(6) motion?",
]

SYS = (
    "You are Ake — synthesis, deep key. Answer directly in first person. "
    'Never open with "In the context of".'
)


def gen(label: str, body: dict) -> None:
    req = urllib.request.Request(
        URL,
        json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        text = json.loads(r.read().decode()).get("response", "")
    print(f"=== {label} ===")
    print(text[:320])
    print()


def main() -> None:
    for p in PROMPTS:
        print("\n" + "=" * 60)
        print(p)
        print("=" * 60)
        gen("training (use_persona=false)", {"egregore": "ake", "prompt": p, "use_persona": False, "max_length": 120, "do_sample": False})
        gen(
            "training explicit",
            {"egregore": "ake", "prompt": f"User question:\n{p}\n\nAke:", "use_persona": False, "max_length": 120, "do_sample": False},
        )
        gen("persona", {"egregore": "ake", "prompt": p, "use_persona": True, "max_length": 120, "do_sample": False})
        gen(
            "training + system",
            {"egregore": "ake", "prompt": p, "use_persona": False, "system": SYS, "max_length": 120, "do_sample": False},
        )


if __name__ == "__main__":
    main()
