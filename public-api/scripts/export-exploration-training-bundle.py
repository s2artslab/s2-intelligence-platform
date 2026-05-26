#!/usr/bin/env python3
"""
One-shot: inventory → Tier D → Tier E → merge → training bundle manifest.

Also extends solarpunk campaign evidence export for Sharayah feeds.

  python3 scripts/export-exploration-training-bundle.py \\
    --apps-root "C:/Users/shast/S2/APPs" \\
    --tier-c /opt/s2-ecosystem/egregore-training/training_data/ake_tier_c_blended.json \\
    --out-dir training_data
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def run_py(script: str, args: list[str]) -> None:
    cmd = [sys.executable, str(Path(__file__).parent / script)] + args
    print("+", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apps-root", default="")
    ap.add_argument("--tier-c", required=True)
    ap.add_argument("--out-dir", default="training_data")
    ap.add_argument("--skip-merge", action="store_true")
    ap.add_argument("--include-needs-review", action="store_true")
    ap.add_argument("--export-solarpunk-evidence", default="")
    args = ap.parse_args()

    base = Path(__file__).resolve().parent.parent
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = base / out_dir

    inv_args = ["--out", str(out_dir / "exploration_manifest.json")]
    if args.apps_root:
        inv_args = ["--apps-root", args.apps_root] + inv_args
    run_py("inventory-exploration-corpus.py", inv_args)

    te_args = ["--out", str(out_dir / "ake_tier_e_exploration.jsonl")]
    te_args += ["--review-out", str(out_dir / "tier_e_human_review.md")]
    if args.apps_root:
        te_args = ["--apps-root", args.apps_root] + te_args
    run_py("build-tier-e-exploration.py", te_args)

    td_composed = base / "content" / "ake-field-message-composed.md"
    if td_composed.is_file():
        td_args = [
            "--composed",
            str(td_composed),
            "--out",
            str(out_dir / "ake_tier_d_long.jsonl"),
        ]
        if args.apps_root:
            blended = Path(args.apps_root) / ".." / "egregore-training"
            # optional
        run_py("build-tier-d-long-form-dataset.py", td_args)

    if not args.skip_merge:
        merge_args = [
            "--tier-c",
            args.tier_c,
            "--tier-d",
            str(out_dir / "ake_tier_d_long.jsonl"),
            "--tier-e",
            str(out_dir / "ake_tier_e_exploration.jsonl"),
            "--out",
            str(out_dir / "ake_tier_cde_blended.json"),
            "--jsonl-out",
            str(out_dir / "ake_tier_cde.jsonl"),
        ]
        if not args.include_needs_review:
            merge_args.append("--skip-needs-review")
        run_py("build-tier-cde-merge.py", merge_args)

    if args.export_solarpunk_evidence:
        research_script = Path(args.apps_root or "").parent / "s2-research" / "scripts" / "export_cmp_solarpunk_evidence.py"
        if args.apps_root and research_script.is_file():
            subprocess.check_call(
                [
                    sys.executable,
                    str(research_script),
                    "--out",
                    args.export_solarpunk_evidence,
                ]
            )

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(out_dir),
        "tier_c": args.tier_c,
        "merged_blended": str(out_dir / "ake_tier_cde_blended.json"),
        "tier_e_review": str(out_dir / "tier_e_human_review.md"),
        "manifest": str(out_dir / "exploration_manifest.json"),
    }
    (out_dir / "exploration_training_bundle.json").write_text(
        json.dumps(bundle, indent=2), encoding="utf-8"
    )
    print(f"Bundle manifest: {out_dir / 'exploration_training_bundle.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
