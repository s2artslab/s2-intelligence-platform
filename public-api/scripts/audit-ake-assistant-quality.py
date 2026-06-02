#!/usr/bin/env python3
"""
Audit / filter Ake training rows for canned assistant openers.

Examples:
  python3 scripts/audit-ake-assistant-quality.py \\
    --input /opt/s2-ecosystem/egregore-training/training_data/ake_tier_c_blended.json

  python3 scripts/audit-ake-assistant-quality.py \\
    --input training_data/ake_tier_c_blended.json \\
    --drop-canned --strip-openers \\
    --out training_data/ake_tier_c_cleaned.json

  python3 scripts/audit-ake-assistant-quality.py \\
    --input training_data/ake_tier_e_exploration.jsonl \\
    --min-score 0.5 --out training_data/ake_tier_e_filtered.jsonl --jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.assistant_quality import (
    extract_assistant_text,
    row_with_cleaned_assistant,
    score_assistant,
    strip_canned_opener,
)


def load_rows(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows
    return json.loads(text)


def save_rows(path: Path, rows: list[dict], jsonl: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if jsonl:
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    else:
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit Ake assistant text quality")
    ap.add_argument("--input", required=True, help="JSON array or JSONL")
    ap.add_argument("--out", default="", help="Write filtered/cleaned dataset")
    ap.add_argument("--jsonl", action="store_true", help="Output JSONL when --out set")
    ap.add_argument(
        "--drop-canned",
        action="store_true",
        help="Drop rows with canned openers (evaluated on raw text before strip)",
    )
    ap.add_argument("--strip-openers", action="store_true", help="Rewrite canned openers when possible")
    ap.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Keep rows with score >= this (default 0 = report only)",
    )
    ap.add_argument("--sample-bad", type=int, default=8, help="Print N example bad rows")
    args = ap.parse_args()

    inp = Path(args.input)
    if not inp.is_file():
        print(f"Missing: {inp}", file=sys.stderr)
        return 1

    rows = load_rows(inp)
    flag_counts: Counter[str] = Counter()
    kept: list[dict] = []
    dropped = 0
    dropped_canned = 0
    stripped = 0
    examples: list[tuple[float, str, str]] = []

    for row in rows:
        text = extract_assistant_text(row)
        raw_rep = score_assistant(text)
        for f in raw_rep.flags:
            flag_counts[f] += 1

        if args.drop_canned and raw_rep.is_canned:
            dropped += 1
            dropped_canned += 1
            if len(examples) < args.sample_bad:
                examples.append((raw_rep.score, text[:200], ",".join(raw_rep.flags)))
            continue

        out_row = row
        rep = raw_rep
        if args.strip_openers and raw_rep.is_canned:
            new_body = strip_canned_opener(text)
            if new_body != text:
                out_row = row_with_cleaned_assistant(row, new_body)
                rep = score_assistant(new_body)
                stripped += 1

        if rep.score < args.min_score:
            dropped += 1
            continue

        kept.append(out_row)

    total = len(rows)
    canned = sum(1 for r in rows if score_assistant(extract_assistant_text(r)).is_canned)

    print(f"Input: {inp} ({total} rows)")
    print(f"Canned-opener rows (heuristic): {canned} ({100 * canned / max(total, 1):.1f}%)")
    print("Flag counts:")
    for flag, n in flag_counts.most_common():
        print(f"  {flag}: {n}")
    if args.strip_openers:
        print(f"Stripped openers: {stripped}")
    if args.drop_canned or args.min_score > 0:
        print(f"Kept: {len(kept)}  Dropped: {dropped}")
        if args.drop_canned:
            print(f"  (dropped canned before strip: {dropped_canned})")

    if examples:
        print("\nSample dropped:")
        for score, snippet, flags in examples:
            print(f"  [{score:.2f} {flags}] {snippet!r}...")

    if args.out:
        out = Path(args.out)
        save_rows(out, kept, args.jsonl or out.suffix == ".jsonl")
        print(f"\nWrote {out} ({len(kept)} rows)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
