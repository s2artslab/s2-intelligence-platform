#!/usr/bin/env python3
"""
Merge Tier C + D + E into one blended JSON for train_egregore_on_foundation_7b.py.

Default mix (by row count targets):
  ~65% Tier C (ake_tier_c_blended.json on r730 or local path)
  ~10% Tier D long (ake_tier_d_long.jsonl)
  ~10% Tier E exploration (ake_tier_e_exploration.jsonl)
  ~15% Tier F cross-egregore synthesis (ake_tier_f_egregore_synthesis.jsonl) when --tier-f set

  python3 scripts/build-tier-cde-merge.py \\
    --tier-c /opt/s2-ecosystem/egregore-training/training_data/ake_tier_c_blended.json \\
    --tier-d training_data/ake_tier_d_long.jsonl \\
    --tier-e training_data/ake_tier_e_exploration.jsonl \\
    --out training_data/ake_tier_cde_blended.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.assistant_quality import extract_assistant_text, score_assistant
from lib.training_row_utils import row_to_blended_item


def _filter_quality(items: list[dict], min_score: float) -> list[dict]:
    if min_score <= 0:
        return items
    kept = []
    for item in items:
        rep = score_assistant(extract_assistant_text(item))
        if rep.score >= min_score and not rep.should_drop:
            kept.append(item)
    return kept


def load_json_array(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier-c", required=True, help="Tier C blended JSON array")
    ap.add_argument("--tier-d", default="", help="Tier D JSONL")
    ap.add_argument("--tier-e", default="", help="Tier E JSONL")
    ap.add_argument("--out", default="training_data/ake_tier_cde_blended.json")
    ap.add_argument("--jsonl-out", default="", help="Optional mirror JSONL")
    ap.add_argument("--tier-f", default="", help="Tier F JSONL — cross-egregore Ake synthesis blend")
    ap.add_argument("--tier-c-ratio", type=float, default=0.65)
    ap.add_argument("--tier-d-ratio", type=float, default=0.10)
    ap.add_argument("--tier-e-ratio", type=float, default=0.10)
    ap.add_argument("--tier-f-ratio", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip-needs-review", action="store_true")
    ap.add_argument(
        "--min-assistant-score",
        type=float,
        default=0.0,
        help="Drop rows whose ake_response scores below this (uses lib.assistant_quality)",
    )
    args = ap.parse_args()

    random.seed(args.seed)
    c_path = Path(args.tier_c)
    if not c_path.is_file():
        print(f"Missing Tier C: {c_path}")
        return 1

    c_items = _filter_quality(load_json_array(c_path), args.min_assistant_score)
    d_rows = load_jsonl(Path(args.tier_d)) if args.tier_d and Path(args.tier_d).is_file() else []
    e_rows = load_jsonl(Path(args.tier_e)) if args.tier_e and Path(args.tier_e).is_file() else []
    f_rows = load_jsonl(Path(args.tier_f)) if args.tier_f and Path(args.tier_f).is_file() else []

    if args.skip_needs_review:
        e_rows = [r for r in e_rows if not (r.get("metadata") or {}).get("needs_review")]

    d_items = _filter_quality([row_to_blended_item(r) for r in d_rows], args.min_assistant_score)
    e_items = _filter_quality([row_to_blended_item(r) for r in e_rows], args.min_assistant_score)
    f_items = _filter_quality([row_to_blended_item(r) for r in f_rows], args.min_assistant_score)

    total_target = len(c_items)
    if total_target < 100:
        total_target = max(1000, len(c_items) + len(d_items) + len(e_items))

    f_ratio = args.tier_f_ratio if f_items else 0.0
    c_ratio = args.tier_c_ratio
    if not f_items and f_ratio > 0:
        c_ratio += f_ratio
        f_ratio = 0.0

    n_c = int(total_target * c_ratio)
    n_d = int(total_target * args.tier_d_ratio)
    n_e = int(total_target * args.tier_e_ratio)
    n_f = int(total_target * f_ratio) if f_items else 0

    if len(c_items) >= n_c:
        c_sample = random.sample(c_items, n_c) if n_c < len(c_items) else list(c_items)
    else:
        c_sample = c_items

    def sample_pool(pool: list, n: int) -> list:
        if not pool:
            return []
        if n <= len(pool):
            return random.sample(pool, n)
        return pool + random.choices(pool, k=n - len(pool))

    merged = (
        c_sample
        + sample_pool(d_items, n_d)
        + sample_pool(e_items, n_e)
        + sample_pool(f_items, n_f)
    )
    random.shuffle(merged)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

    stats = {
        "tier_c_in": len(c_items),
        "tier_d_in": len(d_items),
        "tier_e_in": len(e_items),
        "tier_f_in": len(f_items),
        "merged_total": len(merged),
        "tier_c_used": len(c_sample),
        "tier_d_used": min(n_d, len(d_items)) if d_items else 0,
        "tier_e_used": min(n_e, len(e_items)) if e_items else 0,
        "tier_f_used": min(n_f, len(f_items)) if f_items else 0,
    }
    print(json.dumps(stats, indent=2))
    print(f"Wrote {out}")

    if args.jsonl_out:
        jout = Path(args.jsonl_out)
        with jout.open("w", encoding="utf-8") as f:
            for i, item in enumerate(merged):
                f.write(
                    json.dumps(
                        {
                            "id": f"ake-cde-{i:06d}",
                            "question": item.get("question", ""),
                            "ake_response": item.get("ake_response", ""),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        print(f"Wrote {jout}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
