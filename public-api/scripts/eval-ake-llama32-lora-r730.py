#!/usr/bin/env python3
"""Eval gate: Ollama s2-ake-lora vs s2-ake baseline (Llama 3.2 QLoRA deploy path)."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

DEBRIS_PATTERNS = [
    re.compile(r"^In the context of\b", re.I),
    re.compile(r"^From a \w+ perspective", re.I),
    re.compile(r"^In my view\b", re.I),
    re.compile(r"art of integration", re.I),
    re.compile(r"systems thinking", re.I),
]

SHORT_PROMPTS = [
    "Hi.",
    "What is a motion to dismiss?",
    "Explain qualified immunity in plain language.",
]

LEGAL_PROMPTS = [
    "How should a pro se litigant respond to a Rule 12(b)(6) motion?",
    "What role does jurisdiction play when filing in federal court?",
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


def ollama_chat(base: str, model: str, user: str, timeout: int) -> tuple[float, str]:
    t0 = time.time()
    out = post_json(
        f"{base.rstrip('/')}/api/chat",
        {
            "model": model,
            "messages": [{"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout,
    )
    msg = out.get("message") or {}
    return time.time() - t0, (msg.get("content") or "").strip()


def check_response(text: str, min_len: int = 40) -> list[str]:
    errors = []
    if len(text) < min_len:
        errors.append(f"too short ({len(text)} chars)")
    for pat in DEBRIS_PATTERNS:
        if pat.search(text):
            errors.append(f"debris: {pat.pattern}")
    return errors


def run_suite(
    ollama_url: str,
    model: str,
    prompts: list[str],
    min_len: int,
    timeout: int,
) -> tuple[int, list[float], list[str]]:
    ok = 0
    times: list[float] = []
    failures: list[str] = []
    for p in prompts:
        try:
            elapsed, text = ollama_chat(ollama_url, model, p, timeout)
            times.append(elapsed)
        except Exception as e:
            failures.append(f"{model} '{p[:40]}': {e}")
            print(f"FAIL [{model}] {p!r}: {e}")
            continue
        errs = check_response(text, min_len=min_len)
        if errs:
            failures.append(f"{model} '{p[:40]}': {errs}")
            print(f"FAIL [{model}] {p!r}: {errs}\n  got: {text[:140]!r}")
        else:
            ok += 1
            print(f"OK   [{model}] {elapsed:.1f}s {p!r}: {text[:90]}...")
    return ok, times, failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--lora-model", default="s2-ake-lora")
    ap.add_argument("--baseline-model", default="s2-ake:latest")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--skip-baseline", action="store_true")
    args = ap.parse_args()

    print("=" * 72)
    print(f"Llama 3.2 LoRA eval: {args.lora_model} vs {args.baseline_model}")
    print("=" * 72)

    failures: list[str] = []

    print("\n=== Short prompts (LoRA) ===")
    short_ok, lora_times, f = run_suite(
        args.ollama_url, args.lora_model, SHORT_PROMPTS, 30, args.timeout
    )
    failures.extend(f)

    print("\n=== Legal prompts (LoRA) ===")
    legal_ok, legal_times, f = run_suite(
        args.ollama_url, args.lora_model, LEGAL_PROMPTS, 50, args.timeout
    )
    failures.extend(f)
    lora_times.extend(legal_times)

    if short_ok < 2:
        failures.append(f"LoRA short passed {short_ok}/3 (need >=2)")
    if legal_ok < 1:
        failures.append(f"LoRA legal passed {legal_ok}/2 (need >=1)")

    if not args.skip_baseline:
        print("\n=== Baseline (s2-ake:latest, one prompt) ===")
        try:
            elapsed, text = ollama_chat(
                args.ollama_url,
                args.baseline_model,
                SHORT_PROMPTS[1],
                args.timeout,
            )
            print(f"OK   [{args.baseline_model}] {elapsed:.1f}s: {text[:90]}...")
        except Exception as e:
            print(f"WARN baseline: {e}")

    if lora_times:
        avg = sum(lora_times) / len(lora_times)
        print(f"\nLoRA avg latency: {avg:.1f}s ({len(lora_times)} prompts)")
        if avg > 30:
            failures.append(f"LoRA avg latency {avg:.1f}s > 30s")

    print("\n" + "=" * 72)
    if failures:
        print("EVAL GATE: FAIL")
        for item in failures:
            print(" ", item)
        return 1

    print("EVAL GATE: PASS — consider OLLAMA_PREFER_LORA=true deploy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
