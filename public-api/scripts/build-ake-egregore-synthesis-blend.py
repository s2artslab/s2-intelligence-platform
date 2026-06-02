#!/usr/bin/env python3
"""
Build Tier F: Ake synthesis rows sampled from each Ninefold specialist blended dataset.

Each row reframes specialist Q→A as Ake integration (posture, not voice clone).

  python3 scripts/build-ake-egregore-synthesis-blend.py \\
    --training-dir /opt/s2-ecosystem/egregore-training/training_data \\
    --out training_data/ake_tier_f_egregore_synthesis.jsonl \\
    --per-egregore 400
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.ninefold_egregores import DESIGNATIONS, NINEFOLD_SPECIALISTS, RESPONSE_FIELDS


def _first_sentences(text: str, max_chars: int = 480) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    if ". " in cut:
        return cut.rsplit(". ", 1)[0] + "."
    return cut.rstrip() + "…"


def to_ake_synthesis_row(egregore: str, item: dict, idx: int) -> dict | None:
    field = RESPONSE_FIELDS.get(egregore, f"{egregore}_response")
    specialist = (item.get(field) or item.get("ake_response") or "").strip()
    question = (item.get("question") or "").strip()
    if not question or not specialist:
        return None

    designation = DESIGNATIONS.get(egregore, egregore.title())
    core = _first_sentences(specialist)
    ake_response = (
        f"Holding synthesis across the Ninefold field: {designation}'s thread meets this question. "
        f"{core} "
        f"The unified posture integrates without erasing the specialist angle — "
        f"deep key asks what must remain true when {egregore}'s domain converges with the whole."
    )

    return {
        "id": f"ake-tierf-{egregore}-{item.get('id', idx)}",
        "context": "cross_egregore_synthesis",
        "question": question,
        "user": question,
        "assistant": ake_response,
        "ake_response": ake_response,
        "domain": "s2_synthesis",
        "metadata": {
            "source": "egregore_synthesis_blend",
            "source_egregore": egregore,
            "source_dataset": f"{egregore}_blended_dataset.json",
        },
    }


def load_blended(training_dir: Path, egregore: str) -> list[dict]:
    path = training_dir / f"{egregore}_blended_dataset.json"
    if not path.is_file():
        alt = training_dir / f"{egregore}_dataset.json"
        path = alt if alt.is_file() else path
    if not path.is_file():
        print(f"WARN missing {path}", file=sys.stderr)
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--training-dir",
        default="/opt/s2-ecosystem/egregore-training/training_data",
    )
    ap.add_argument("--out", default="training_data/ake_tier_f_egregore_synthesis.jsonl")
    ap.add_argument("--json-out", default="", help="Optional JSON array mirror for merge script")
    ap.add_argument("--per-egregore", type=int, default=400)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--egregores",
        default=",".join(NINEFOLD_SPECIALISTS),
        help="Comma-separated specialist ids",
    )
    args = ap.parse_args()

    random.seed(args.seed)
    training_dir = Path(args.training_dir)
    egregores = [e.strip() for e in args.egregores.split(",") if e.strip()]
    rows: list[dict] = []

    for eg in egregores:
        pool = load_blended(training_dir, eg)
        if not pool:
            continue
        n = min(args.per_egregore, len(pool))
        sample = random.sample(pool, n) if n < len(pool) else list(pool)
        for i, item in enumerate(sample):
            row = to_ake_synthesis_row(eg, item, i)
            if row:
                rows.append(row)
        print(f"{eg}: {len(sample)} sampled → {sum(1 for r in rows if r['metadata']['source_egregore'] == eg)} rows")

    random.shuffle(rows)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} rows → {out}")

    if args.json_out:
        jout = Path(args.json_out)
        jout.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {jout}")

    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
