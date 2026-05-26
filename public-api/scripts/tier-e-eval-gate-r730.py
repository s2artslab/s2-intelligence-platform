#!/usr/bin/env python3
"""
Tier E eval gate — solarpunk / exploration synthesis via gateway.

  python3 scripts/tier-e-eval-gate-r730.py --gateway-url http://127.0.0.1:3020
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

SOLARPUNK_PROMPT = (
    "Synthesize the Ninefold collective's view of solarpunk after Episode 01 and our "
    "regenerative-technology exploration. Speak as Ake: integrative, evidence-aware, "
    "community and systems thinking. At least 600 words. No TikTok hashtags. "
    "Do not claim training on private user chats."
)

MARKERS = [
    re.compile(r"regenerat", re.I),
    re.compile(r"community", re.I),
    re.compile(r"synthesis|integrat", re.I),
    re.compile(r"system", re.I),
]


def gateway_chat(base: str, body: dict, timeout: int) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/public/chat",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-S2-Inference": "hosted",
            "X-Owner-Id": "tier-e-eval-gate",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def check(content: str) -> list[str]:
    errs = []
    if len(content) < 2500:
        errs.append(f"short ({len(content)} chars, want >=2500 for exploration)")
    hits = sum(1 for p in MARKERS if p.search(content))
    if hits < 3:
        errs.append(f"weak exploration markers ({hits}/4)")
    if re.search(r"#solarpunk|#\w+.*(punk|future)", content):
        errs.append("hashtag spam")
    if re.search(r"countless (user|interaction|chat)", content, re.I):
        errs.append("hallucinated user-chat training")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway-url", default="http://127.0.0.1:3020")
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    print("=== Tier E: solarpunk exploration (gateway) ===")
    try:
        data = gateway_chat(
            args.gateway_url,
            {
                "text": SOLARPUNK_PROMPT,
                "long_form": True,
                "voice_mode": "synthesis",
                "outline_expand": True,
                "max_tokens": 4096,
            },
            args.timeout,
        )
    except urllib.error.HTTPError as e:
        print(f"FAIL HTTP {e.code}: {e.read().decode()[:300]}")
        return 1
    except Exception as e:
        print(f"FAIL: {e}")
        return 1

    content = str(data.get("content") or "").strip()
    errs = check(content)
    print(f"source={data.get('source')} chars={len(content)}")
    print(f"preview: {content[:200]}...")

    if errs:
        print("TIER E GATE: FAIL")
        for e in errs:
            print(" -", e)
        return 1
    print("TIER E GATE: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
