#!/usr/bin/env python3
"""
Distill Ninefold egregore blended datasets → compact BitNet b1.58 JSONL (llamacpp format).

One JSONL per egregore for LoRA fine-tune on BitNet-b1.58-2B-4T.

  python3 scripts/build-bitnet-egregore-dataset.py \\
    --training-dir /opt/s2-ecosystem/egregore-training/training_data \\
    --out-dir /opt/s2-ecosystem/egregore-training/training_data/bitnet_egregores \\
    --per-egregore 800
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.assistant_quality import score_assistant, strip_canned_opener
from lib.ninefold_egregores import DESIGNATIONS, NINEFOLD_SPECIALISTS, RESPONSE_FIELDS


def egregore_prompt(egregore: str, question: str) -> str:
    cap = egregore.capitalize()
    designation = DESIGNATIONS.get(egregore, cap)
    q = question.strip()
    return (
        f"Egregore: {cap} ({designation})\n"
        f"Task: compact\n"
        f"Reply in under 80 words.\n\n"
        f"User: {q}\n"
        f"{cap}:"
    )


def trim_response(text: str, max_words: int = 80) -> str:
    text = re.sub(r"\s+", " ", text.strip())
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--training-dir",
        default="/opt/s2-ecosystem/egregore-training/training_data",
    )
    ap.add_argument("--out-dir", default="training_data/bitnet_egregores")
    ap.add_argument("--per-egregore", type=int, default=800)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--egregores",
        default=",".join(NINEFOLD_SPECIALISTS),
    )
    ap.add_argument("--include-ake", action="store_true", help="Also build ake compact synthesis lane")
    ap.add_argument(
        "--min-score",
        type=float,
        default=0.5,
        help="Drop blended rows with canned/low-quality assistant text (default 0.5)",
    )
    ap.add_argument(
        "--strip-openers",
        action="store_true",
        default=True,
        help="Strip canned openers from completions when possible (default on)",
    )
    ap.add_argument(
        "--no-strip-openers",
        action="store_false",
        dest="strip_openers",
        help="Disable opener stripping",
    )
    args = ap.parse_args()

    random.seed(args.seed)
    training_dir = Path(args.training_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    egregores = [e.strip() for e in args.egregores.split(",") if e.strip()]
    if args.include_ake:
        egregores = list(egregores) + ["ake"]

    registry: dict[str, str] = {}
    total = 0

    for eg in egregores:
        blended = training_dir / f"{eg}_blended_dataset.json"
        if not blended.is_file():
            print(f"WARN skip {eg}: missing {blended}", file=sys.stderr)
            continue

        pool = json.loads(blended.read_text(encoding="utf-8"))
        field = RESPONSE_FIELDS.get(eg, f"{eg}_response")
        n = min(args.per_egregore, len(pool))
        sample = random.sample(pool, n) if n < len(pool) else list(pool)

        out_path = out_dir / f"bitnet_{eg}.jsonl"
        written = 0
        skipped = 0
        with out_path.open("w", encoding="utf-8") as f:
            for item in sample:
                q = (item.get("question") or "").strip()
                resp = (item.get(field) or item.get("ake_response") or "").strip()
                if not q or not resp:
                    skipped += 1
                    continue
                qual = score_assistant(resp)
                if qual.score < args.min_score or qual.should_drop:
                    skipped += 1
                    continue
                if args.strip_openers:
                    resp = strip_canned_opener(resp)
                if not resp or len(resp.split()) < 8:
                    skipped += 1
                    continue
                row = {
                    "id": f"bitnet-{eg}-{item.get('id', written)}",
                    "egregore": eg,
                    "prompt": egregore_prompt(eg, q),
                    "completion": trim_response(resp),
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                written += 1

        registry[eg] = str(out_path)
        total += written
        print(f"{eg}: {written} rows → {out_path} (skipped {skipped} low-quality)")

    reg_path = out_dir / "bitnet_egregore_datasets.json"
    reg_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(f"Registry: {reg_path} ({total} total rows)")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
