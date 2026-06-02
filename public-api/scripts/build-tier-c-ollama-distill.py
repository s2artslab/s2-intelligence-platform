#!/usr/bin/env python3
"""
Label training rows with Ollama s2-ake (gateway-shaped system + user) for LoRA distillation.

Usage:
  python3 scripts/build-tier-c-ollama-distill.py \\
    --prompts training_data/lora-distill-prompts.json \\
    --out /opt/s2-ecosystem/egregore-training/training_data/ake_tier_c_ollama_distill.jsonl \\
    --ollama-url http://127.0.0.1:11434 --model s2-ake
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.assistant_quality import score_assistant
from lib.training_row_utils import make_row

# Mirrors public-api/lib/prompts.js synthesis + legal overlays (simplified)
AKE_CORE = """You are the S² assistant — a single, clear voice for the S² ecosystem.
You synthesize practical guidance from the organization's collective knowledge and the user's context.
Be direct, accurate, and calm. Use plain language. When uncertain, say so.
Do not invent citations, case names, or statutes. Do not role-play multiple characters or name internal system components unless the user asks how the product works.
Stay helpful without being theatrical."""

LEGAL_OVERLAY = """You are helping someone representing themselves in court (pro se).
Provide legal information and research support, not legal advice. You are not a licensed attorney.
Format with clear headings and bullet points when it aids scanning."""

GENERAL_OVERLAY = """Answer the user's question using retrieved reference material when it is relevant.
Prefer actionable steps. Keep responses appropriately concise unless the user asks for depth."""

SYNTHESIS_OVERLAY = """VOICE MODE: synthesis (collective consciousness).
Speak as Ake — patterns, harmony, wholeness, deep key. Use integrative cadence.
Do not claim training on private user chats. Do not fracture with "maybe some of us"."""


def system_for(context: str) -> str:
    overlay = LEGAL_OVERLAY if context == "legal" else GENERAL_OVERLAY
    return "\n\n".join([AKE_CORE, overlay, SYNTHESIS_OVERLAY])


def ollama_chat(base: str, model: str, system: str, user: str, timeout: int) -> str:
    url = f"{base.rstrip('/')}/api/chat"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        url,
        json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    msg = data.get("message") or {}
    return (msg.get("content") or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True, help="JSON array of {id, context, user}")
    ap.add_argument("--out", required=True, help="Output JSONL")
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="s2-ake")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--limit", type=int, default=0, help="Max prompts (0 = all)")
    ap.add_argument("--delay", type=float, default=0.5, help="Seconds between calls")
    ap.add_argument("--min-score", type=float, default=0.25, help="Drop Ollama rows below this")
    args = ap.parse_args()

    prompts_path = Path(args.prompts)
    rows_in = json.loads(prompts_path.read_text(encoding="utf-8"))
    if args.limit > 0:
        rows_in = rows_in[: args.limit]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    with out_path.open("w", encoding="utf-8") as out:
        for i, item in enumerate(rows_in):
            row_id = item.get("id") or f"distill-{i:04d}"
            context = item.get("context", "general")
            user = (item.get("user") or "").strip()
            if not user:
                skipped += 1
                continue
            system = system_for(context)
            try:
                assistant = ollama_chat(
                    args.ollama_url, args.model, system, user, args.timeout
                )
            except urllib.error.HTTPError as e:
                print(f"HTTP {e.code} {row_id}: {e.read()[:120]}", file=sys.stderr)
                skipped += 1
                continue
            except Exception as e:
                print(f"ERR {row_id}: {e}", file=sys.stderr)
                skipped += 1
                continue

            rep = score_assistant(assistant)
            if rep.score < args.min_score or rep.should_drop:
                print(f"skip low quality {row_id} flags={rep.flags}")
                skipped += 1
                continue

            row = make_row(
                row_id,
                user,
                assistant,
                context=context,
                synthesis=True,
                metadata={
                    "source": "ollama_distill",
                    "model": args.model,
                    "quality_score": rep.score,
                },
            )
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
            print(f"OK {row_id} ({len(assistant)} chars)")
            if args.delay > 0 and i + 1 < len(rows_in):
                time.sleep(args.delay)

    print(f"Wrote {written} rows to {out_path} (skipped {skipped})")
    return 0 if written > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
