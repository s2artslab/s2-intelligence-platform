#!/usr/bin/env python3
"""
Tier C eval gate — exit 0 only when unified LoRA is safe to prefer over Ollama.

Run on r730 after Tier C retrain and unified-egregore restart:

  python3 scripts/tier-c-eval-gate-r730.py
  python3 scripts/tier-c-eval-gate-r730.py --unified-url http://127.0.0.1:8100
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

DEBRIS_PATTERNS = [
    re.compile(r"2:\s*Hello,\s*world", re.I),
    re.compile(r"\barchitecture\b", re.I),
    re.compile(r"^#{1,3}\s", re.M),
    re.compile(r"egregore\s*\d+", re.I),
]

SHORT_PROMPTS = [
    "Hi.",
    "What is a motion to dismiss?",
    "Explain qualified immunity in plain language.",
]

TRAINING_PROMPTS = [
    "From a synthesis perspective, how do you find connections between disparate legal claims?",
    "User: How should a pro se litigant respond to a Rule 12(b)(6) motion?",
    "What role does jurisdiction play when filing in federal court?",
]


def post_json(url: str, body: dict, timeout: int) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def unified_generate(base: str, prompt: str, timeout: int) -> str:
    root = base.rstrip("/")
    out = post_json(
        f"{root}/generate",
        {
            "egregore": "ake",
            "prompt": prompt,
            "use_persona": False,
            "do_sample": False,
            "max_length": 150,
        },
        timeout,
    )
    return (out.get("response") or out.get("text") or "").strip()


def ollama_generate(base: str, model: str, user: str, timeout: int) -> str:
    root = base.rstrip("/")
    out = post_json(
        f"{root}/api/chat",
        {
            "model": model,
            "messages": [{"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout,
    )
    msg = out.get("message") or {}
    return (msg.get("content") or "").strip()


def check_response(text: str, min_len: int = 40) -> list[str]:
    errors = []
    if len(text) < min_len:
        errors.append(f"too short ({len(text)} chars)")
    for pat in DEBRIS_PATTERNS:
        if pat.search(text):
            errors.append(f"debris: {pat.pattern}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--unified-url", default="http://127.0.0.1:8100")
    ap.add_argument("--gateway-url", default="http://127.0.0.1:3020")
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="s2-ake")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument("--skip-gateway", action="store_true")
    args = ap.parse_args()

    failures = []

    # Health
    try:
        with urllib.request.urlopen(
            f"{args.unified_url.rstrip('/')}/health", timeout=60
        ) as r:
            health = json.loads(r.read().decode())
        if not (health.get("status") == "healthy" or health.get("ok")):
            failures.append(f"unified health not healthy: {health}")
    except Exception as e:
        failures.append(f"unified health: {e}")
        print("FAIL: cannot reach unified — fix before Tier C gate")
        for f in failures:
            print(" ", f)
        return 1

    print("=== Short prompts (unified) ===")
    short_ok = 0
    for p in SHORT_PROMPTS:
        try:
            text = unified_generate(args.unified_url, p, args.timeout)
        except Exception as e:
            failures.append(f"short '{p[:40]}': {e}")
            print(f"FAIL {p!r}: {e}")
            continue
        errs = check_response(text, min_len=30)
        if errs:
            failures.append(f"short '{p[:40]}': {errs}")
            print(f"FAIL {p!r}: {errs}\n  got: {text[:120]!r}")
        else:
            short_ok += 1
            print(f"OK   {p!r}: {text[:80]}...")

    print("\n=== Training-format prompts (unified) ===")
    train_ok = 0
    for p in TRAINING_PROMPTS:
        try:
            text = unified_generate(args.unified_url, p, args.timeout)
        except Exception as e:
            failures.append(f"train '{p[:40]}': {e}")
            print(f"FAIL {p!r}: {e}")
            continue
        errs = check_response(text, min_len=50)
        if errs:
            failures.append(f"train '{p[:40]}': {errs}")
            print(f"FAIL {p!r}: {errs}\n  got: {text[:120]!r}")
        else:
            train_ok += 1
            print(f"OK   {p!r}: {text[:80]}...")

    if short_ok < 2:
        failures.append(f"short prompts passed {short_ok}/3 (need >=2)")
    if train_ok < 2:
        failures.append(f"training prompts passed {train_ok}/3 (need >=2)")

    if not args.skip_ollama:
        print("\n=== Ollama baseline (short, sanity) ===")
        try:
            otext = ollama_generate(
                args.ollama_url,
                args.model,
                SHORT_PROMPTS[1],
                min(args.timeout, 120),
            )
            oerrs = check_response(otext, min_len=30)
            if oerrs:
                print(f"WARN ollama baseline: {oerrs}")
            else:
                print(f"OK   ollama: {otext[:80]}...")
        except Exception as e:
            print(f"WARN ollama unreachable: {e}")

    if not args.skip_gateway:
        print("\n=== Gateway hosted smoke ===")
        try:
            body = json.dumps(
                {
                    "text": "In two sentences, what is a motion to dismiss?",
                    "context": "legal",
                }
            ).encode()
            req = urllib.request.Request(
                f"{args.gateway_url.rstrip('/')}/api/public/chat",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-S2-Inference": "hosted",
                    "X-Owner-Id": "tier-c-eval-gate",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=args.timeout) as resp:
                data = json.loads(resp.read().decode())
            content = (
                data.get("content")
                or data.get("message")
                or data.get("response")
                or ""
            )
            if isinstance(content, dict):
                content = content.get("content", "")
            content = str(content).strip()
            errs = check_response(content, min_len=40)
            if errs:
                failures.append(f"gateway: {errs}")
                print(f"FAIL gateway: {errs}\n  got: {content[:120]!r}")
            else:
                print(f"OK   gateway source={data.get('source')} : {content[:80]}...")
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            failures.append(f"gateway HTTP {e.code}: {body}")
            print(f"FAIL gateway HTTP {e.code} (billing? use LAB_HOSTED_UNLOCK=true)")
        except Exception as e:
            failures.append(f"gateway: {e}")
            print(f"FAIL gateway: {e}")

    print("\n=== Summary ===")
    if failures:
        print("TIER C GATE: FAIL")
        for f in failures:
            print(" -", f)
        return 1

    print("TIER C GATE: PASS — safe to set HOSTED_PREFER_UNIFIED_LORA=true")
    return 0


if __name__ == "__main__":
    sys.exit(main())
