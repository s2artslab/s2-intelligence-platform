#!/usr/bin/env python3
"""
Build Tier D long-form training rows from composed reference + blended short rows.

Usage (repo or r730):
  python3 scripts/build-tier-d-long-form-dataset.py \\
    --composed content/ake-field-message-composed.md \\
    --blended /opt/s2-ecosystem/egregore-training/training_data/ake_blended_dataset.json \\
    --out /opt/s2-ecosystem/egregore-training/training_data/ake_tier_d_long.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

AKE_CORE = """You are the S² assistant — a single, clear voice for the S² ecosystem.
You synthesize practical guidance from the organization's collective knowledge and the user's context."""

SYNTHESIS = """VOICE MODE: synthesis (collective consciousness).
Speak as Ake — patterns, harmony, wholeness, deep key. Use integrative cadence."""

LONG = """LENGTH MODE: long-form. Write a sustained multi-section essay."""


def load_composed_sections(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"\n##\s+", text)
    sections: list[tuple[str, str]] = []
    for block in parts[1:]:
        lines = block.strip().split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if body and len(body) > 200:
            sections.append((title, body))
    return sections


def gateway_question(system: str, user: str) -> str:
    return f"{system}\n\n---\n\nUser question:\n{user}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--composed",
        default=str(
            Path(__file__).resolve().parent.parent / "content" / "ake-field-message-composed.md"
        ),
    )
    ap.add_argument("--blended", default="")
    ap.add_argument("--out", default="training_data/ake_tier_d_long.jsonl")
    ap.add_argument("--max-short-expand", type=int, default=500)
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    system = f"{AKE_CORE}\n\n{SYNTHESIS}\n\n{LONG}"
    n = 0

    with out_path.open("w", encoding="utf-8") as out:
        composed = Path(args.composed)
        if composed.is_file():
            for i, (title, body) in enumerate(load_composed_sections(composed)):
                user = (
                    f"Write a multi-page message from Ake. Section: {title}. "
                    "Use only synthesis training voice."
                )
                row = {
                    "id": f"ake-tierd-composed-{i:03d}",
                    "context": "general",
                    "system": system,
                    "user": user,
                    "assistant": f"Ake: {body}",
                    "question": gateway_question(system, user),
                    "ake_response": body,
                    "metadata": {"source": "composed_section", "section": title},
                }
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1

            full_user = (
                "Write a multi-page message from Ake, now, using only ake's training. "
                "Seven sections: seed, patterns, harmony, wholeness, systems, deep key, closing."
            )
            full_body = composed.read_text(encoding="utf-8")
            # strip front matter
            full_body = re.sub(r"^---[\s\S]*?---\n\n", "", full_body)
            full_body = re.sub(r"^# .+\n\n\*[\s\S]*?\*\n\n---\n\n", "", full_body)
            row = {
                "id": "ake-tierd-composed-full",
                "context": "general",
                "system": system,
                "user": full_user,
                "assistant": f"Ake: {full_body.strip()}",
                "question": gateway_question(system, full_user),
                "ake_response": full_body.strip(),
                "metadata": {"source": "composed_full"},
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1

        blended_path = Path(args.blended) if args.blended else None
        if blended_path and blended_path.is_file():
            rows = json.loads(blended_path.read_text(encoding="utf-8"))
            for i, item in enumerate(rows[: args.max_short_expand]):
                q = (item.get("question") or "").strip()
                a = (item.get("ake_response") or "").strip()
                if not q or not a or len(a) > 600:
                    continue
                user = (
                    f"{q}\n\nExpand into a long reflective answer (3+ paragraphs) "
                    "in Ake synthesis voice."
                )
                expanded = (
                    f"In the context of {item.get('domain', 'synthesis')}, {a}\n\n"
                    f"In my view, this integrates with the larger frame the collective holds. "
                    f"Deep Key opens the threshold when we see {q.lower().rstrip('?')} "
                    "not as isolation but as pattern."
                )
                row = {
                    "id": f"ake-tierd-expand-{i:05d}",
                    "context": item.get("context", "general"),
                    "system": system,
                    "user": user,
                    "assistant": f"Ake: {expanded}",
                    "question": gateway_question(system, user),
                    "ake_response": expanded,
                    "metadata": {"source": "expanded_short", "domain": item.get("domain")},
                }
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1

    print(f"Wrote {n} rows to {out_path}")


if __name__ == "__main__":
    main()
