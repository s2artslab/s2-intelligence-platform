#!/usr/bin/env python3
"""End-to-end hosted eval: gateway /api/lab/hosted/chat → Ollama s2-ake-lora."""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

DEBRIS = [
    re.compile(r"^In the context of\b", re.I),
    re.compile(r"^From a \w+ perspective", re.I),
    re.compile(r"^#{1,3}\s", re.M),
]

PROMPTS = [
    ("Hi.", "general", 30),
    ("What is a motion to dismiss?", "legal", 40),
    ("Explain qualified immunity in plain language.", "legal", 40),
    (
        "How should a pro se litigant respond to a Rule 12(b)(6) motion?",
        "legal",
        50,
    ),
]


def post_json(url: str, body: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url,
        json.dumps(body).encode(),
        {"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway-url", default="http://127.0.0.1:3020")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()
    base = args.gateway_url.rstrip("/")
    url = f"{base}/api/lab/hosted/chat"

    print("=== Hosted lab chat end-to-end (Ollama s2-ake-lora via gateway) ===")
    ok = 0
    failures: list[str] = []

    for prompt, context, min_len in PROMPTS:
        try:
            data = post_json(
                url,
                {"message": prompt, "context": context, "max_tokens": 150},
                args.timeout,
            )
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            failures.append(f"{prompt[:40]}: HTTP {e.code}")
            print(f"FAIL {prompt!r}: HTTP {e.code} {body}")
            continue
        except Exception as e:
            failures.append(f"{prompt[:40]}: {e}")
            print(f"FAIL {prompt!r}: {e}")
            continue

        content = str(data.get("content") or "").strip()
        model = data.get("model", "")
        lat = data.get("latency_ms", "?")

        if not data.get("ok"):
            failures.append(f"{prompt[:40]}: {data.get('error')}")
            print(f"FAIL {prompt!r}: {data}")
            continue
        if len(content) < min_len:
            failures.append(f"{prompt[:40]}: too short ({len(content)} chars)")
            print(f"FAIL {prompt!r}: too short ({len(content)} chars)")
            continue
        debris = [pat.pattern for pat in DEBRIS if pat.search(content)]
        if debris:
            failures.append(f"{prompt[:40]}: debris {debris}")
            print(f"FAIL {prompt!r}: debris\n  {content[:120]!r}")
            continue

        ok += 1
        print(f"OK   {lat}ms model={model} {prompt!r}: {content[:90]}...")

    print(f"\n=== Summary: {ok}/{len(PROMPTS)} passed ===")
    if failures:
        print("HOSTED EVAL: FAIL")
        for item in failures:
            print(" -", item)
        return 1

    print("HOSTED EVAL: PASS — gateway → Ollama s2-ake-lora end-to-end OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
