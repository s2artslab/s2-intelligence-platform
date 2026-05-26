#!/usr/bin/env python3
"""
Tier D eval gate — long-form + synthesis voice via gateway.

  python3 scripts/tier-d-eval-gate-r730.py --gateway-url http://127.0.0.1:3020

Requires LAB_HOSTED_UNLOCK=true or valid billing owner on gateway .env.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

FIELD_MESSAGE_PROMPT = (
    "Write a multi-page message from Ake, now, using only ake's training. "
    "Speak as the collective consciousness: synthesis, patterns, harmony, wholeness, deep key."
)

SYNTHESIS_MARKERS = [
    re.compile(r"in my view", re.I),
    re.compile(r"in the context of", re.I),
    re.compile(r"synthesis", re.I),
    re.compile(r"deep key", re.I),
    re.compile(r"wholeness|harmony|patterns", re.I),
]

HALLUCINATION = re.compile(
    r"countless interactions with users|trained on (?:your|private) (?:chats|conversations)",
    re.I,
)


def gateway_long_form(base: str, timeout: int) -> dict:
    body = json.dumps(
        {
            "text": FIELD_MESSAGE_PROMPT,
            "context": "general",
            "long_form": True,
            "voice_mode": "synthesis",
            "outline_expand": True,
            "max_tokens": 4096,
        }
    ).encode()
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/public/chat",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-S2-Inference": "hosted",
            "X-Owner-Id": "tier-d-eval-gate",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def check_long_form(data: dict) -> list[str]:
    errors = []
    content = str(data.get("content") or data.get("response") or "").strip()
    if len(content) < 4000:
        errors.append(f"too short for long-form ({len(content)} chars, want >=4000)")
    markers = sum(1 for p in SYNTHESIS_MARKERS if p.search(content))
    if markers < 3:
        errors.append(f"weak synthesis voice ({markers}/5 marker groups)")
    if HALLUCINATION.search(content):
        errors.append("hallucinated private-chat training claim")
    if not data.get("long_form") and "long-form" not in str(data.get("source", "")):
        errors.append(f"not long_form response source={data.get('source')}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway-url", default="http://127.0.0.1:3020")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    print("=== Tier D: gateway long-form + synthesis ===")
    try:
        data = gateway_long_form(args.gateway_url, args.timeout)
    except urllib.error.HTTPError as e:
        print(f"FAIL HTTP {e.code}: {e.read().decode()[:300]}")
        return 1
    except Exception as e:
        print(f"FAIL: {e}")
        return 1

    content = str(data.get("content") or "")[:200]
    errs = check_long_form(data)
    print(f"source={data.get('source')} chars={len(str(data.get('content') or ''))}")
    print(f"outline_expand={data.get('outline_expand')} sections={data.get('sections')}")
    print(f"preview: {content}...")

    if errs:
        print("TIER D GATE: FAIL")
        for e in errs:
            print(" -", e)
        return 1

    print("TIER D GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
