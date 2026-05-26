#!/usr/bin/env python3
"""
Build Tier C v2 JSONL from ake_blended_dataset.json (gateway-shaped system blocks).

Run on r730:
  python3 /opt/s2-ecosystem/public-api/scripts/build-tier-c-v2-from-blended.py
"""
from __future__ import annotations

import json
from pathlib import Path

AKE_CORE = """You are the S² assistant — a single, clear voice for the S² ecosystem.
You synthesize practical guidance from the organization's collective knowledge and the user's context.
Be direct, accurate, and calm. Use plain language. When uncertain, say so.
Do not invent citations, case names, or statutes. Do not role-play multiple characters or name internal system components unless the user asks how the product works.
Stay helpful without being theatrical."""

LEGAL = """You are helping someone representing themselves in court (pro se).
Provide legal information and research support, not legal advice. You are not a licensed attorney.
Format with clear headings and bullet points when it aids scanning."""

GENERAL = """Answer the user's question using retrieved reference material when it is relevant.
Prefer actionable steps. Keep responses appropriately concise unless the user asks for depth."""

BASE = Path("/opt/s2-ecosystem/egregore-training")
SRC = BASE / "training_data" / "ake_blended_dataset.json"
OUT_JSONL = BASE / "training_data" / "ake_tier_c_v2.jsonl"
OUT_BLENDED = BASE / "training_data" / "ake_tier_c_blended.json"


def main() -> None:
    with SRC.open(encoding="utf-8") as f:
        rows = json.load(f)

    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    blended_out = []
    n = 0
    with OUT_JSONL.open("w", encoding="utf-8") as out:
        for i, item in enumerate(rows):
            q = (item.get("question") or "").strip()
            a = (item.get("ake_response") or "").strip()
            if not q or not a:
                continue
            if a.startswith("Ake:"):
                a = a[4:].lstrip()
            ctx = "legal" if any(
                w in q.lower() for w in ("court", "motion", "rule", "plaintiff", "defendant", "filing", "pro se")
            ) else "general"
            system = f"{AKE_CORE}\n\n{LEGAL if ctx == 'legal' else GENERAL}"
            gateway_q = f"{system}\n\n---\n\nUser question:\n{q}"
            line = {
                "id": f"ake-tierc-v2-{i:05d}",
                "context": ctx,
                "system": system,
                "user": q,
                "assistant": f"Ake: {a}",
            }
            out.write(json.dumps(line, ensure_ascii=False) + "\n")
            blended_out.append({"question": gateway_q, "ake_response": a})
            n += 1

    with OUT_BLENDED.open("w", encoding="utf-8") as bf:
        json.dump(blended_out, bf, ensure_ascii=False, indent=2)

    print(f"Wrote {n} rows to {OUT_JSONL} and {OUT_BLENDED}")


if __name__ == "__main__":
    main()
