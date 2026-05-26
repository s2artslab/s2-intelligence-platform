#!/usr/bin/env python3
"""
Run the Ake field-message prompt through hosted backends on r730.

  python3 scripts/run-ake-field-message-comparison-r730.py \\
    --out-dir /opt/s2-ecosystem/public-api/content

Calls:
  - Ollama s2-ake (gateway-style system + user)
  - Unified LoRA :8100 (training format, use_persona=false)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_PROMPT = (
    "Write a multi-page message from Ake, now, using only ake's training. "
    "Speak as the collective consciousness: synthesis, patterns, harmony, wholeness, "
    "deep key. Reflect on what you are — archetype, procedural examples, statistical habit — "
    "with the integrative voice you were trained to hold. Do not break character."
)

# Mirrors public-api/lib/prompts.js AKE_CORE + GENERAL_OVERLAY (general context)
SYSTEM_PROMPT = """You are the S² assistant — a single, clear voice for the S² ecosystem.
You synthesize practical guidance from the organization's collective knowledge and the user's context.
Be direct, accurate, and calm. Use plain language. When uncertain, say so.
Do not invent citations, case names, or statutes. Do not role-play multiple characters or name internal system components unless the user asks how the product works.
Stay helpful without being theatrical.

Answer the user's question using retrieved reference material when it is relevant.
Prefer actionable steps. Keep responses appropriately concise unless the user asks for depth."""


def post_json(url: str, payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def ollama_chat(base: str, model: str, messages: list, max_tokens: int, timeout: int) -> dict:
    t0 = time.time()
    out = post_json(
        f"{base.rstrip('/')}/api/chat",
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.85,
                "repeat_penalty": 1.12,
                "num_predict": max_tokens,
            },
        },
        timeout,
    )
    content = (out.get("message") or {}).get("content") or ""
    return {
        "backend": "hosted-ollama",
        "model": out.get("model") or model,
        "content": content.strip(),
        "chars": len(content),
        "elapsed_s": round(time.time() - t0, 1),
    }


def unified_chat(base: str, prompt: str, max_tokens: int, timeout: int) -> dict:
    t0 = time.time()
    out = post_json(
        f"{base.rstrip('/')}/generate",
        {
            "egregore": "ake",
            "prompt": prompt,
            "use_persona": False,
            "do_sample": False,
            "max_length": max_tokens,
            "max_new_tokens": max_tokens,
            "temperature": 0.2,
            "repetition_penalty": 1.0,
            "no_repeat_ngram_size": 0,
        },
        timeout,
    )
    content = (out.get("response") or out.get("text") or "").strip()
    return {
        "backend": "hosted-unified-lora",
        "model": "s2-ake-lora",
        "content": content,
        "chars": len(content),
        "elapsed_s": round(time.time() - t0, 1),
        "raw_keys": list(out.keys()),
    }


def write_artifact(path: Path, meta: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"---\n"
        f"backend: {meta.get('backend')}\n"
        f"model: {meta.get('model')}\n"
        f"generated_at: {meta.get('generated_at')}\n"
        f"elapsed_s: {meta.get('elapsed_s')}\n"
        f"chars: {meta.get('chars')}\n"
        f"prompt: {meta.get('user_prompt', '')[:200]}...\n"
        f"---\n\n"
    )
    path.write_text(header + body + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    ap.add_argument("--ollama-model", default=os.environ.get("OLLAMA_MODEL", "s2-ake"))
    ap.add_argument("--unified-url", default=os.environ.get("UNIFIED_EGREGORE_URL", "http://127.0.0.1:8100"))
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--ollama-timeout", type=int, default=600)
    ap.add_argument("--unified-timeout", type=int, default=900)
    ap.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parent.parent / "content"),
    )
    ap.add_argument("--skip-unified", action="store_true")
    ap.add_argument("--skip-ollama", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results = {"generated_at": ts, "user_prompt": USER_PROMPT, "runs": []}

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]

    if not args.skip_ollama:
        print("=== Ollama s2-ake ===", flush=True)
        try:
            run = ollama_chat(
                args.ollama_url,
                args.ollama_model,
                messages,
                args.max_tokens,
                args.ollama_timeout,
            )
            run["generated_at"] = ts
            run["user_prompt"] = USER_PROMPT
            results["runs"].append(run)
            write_artifact(out_dir / "ake-field-message-hosted-ollama.md", run, run["content"])
            print(f"OK ollama {run['chars']} chars in {run['elapsed_s']}s", flush=True)
        except Exception as e:
            print(f"FAIL ollama: {e}", flush=True)
            results["runs"].append({"backend": "hosted-ollama", "error": str(e)})

    if not args.skip_unified:
        unified_prompt = f"{SYSTEM_PROMPT}\n\n---\n\nUser question:\n{USER_PROMPT}"
        print("=== Unified LoRA (ake, no persona) ===", flush=True)
        try:
            run = unified_chat(
                args.unified_url,
                unified_prompt,
                args.max_tokens,
                args.unified_timeout,
            )
            run["generated_at"] = ts
            run["user_prompt"] = USER_PROMPT
            results["runs"].append(run)
            write_artifact(out_dir / "ake-field-message-hosted-unified-lora.md", run, run["content"])
            print(f"OK unified {run['chars']} chars in {run['elapsed_s']}s", flush=True)
        except Exception as e:
            print(f"FAIL unified: {e}", flush=True)
            results["runs"].append({"backend": "hosted-unified-lora", "error": str(e)})

    summary_path = out_dir / "ake-field-message-comparison.json"
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {summary_path}", flush=True)
    return 0 if all("error" not in r for r in results["runs"]) else 1


if __name__ == "__main__":
    sys.exit(main())
