#!/usr/bin/env python3
"""
Inventory exploration sources for Ake training / RAG.

  python3 scripts/inventory-exploration-corpus.py --out training_data/exploration_manifest.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from lib.corpus_paths import (
    apps_root,
    ninefold_egregorelab,
    s2_forge_rag,
    s2_marketing_docs,
    s2_research,
)


def scan_glob(base: Path, pattern: str, category: str) -> list[dict]:
    if not base.is_dir():
        return []
    items = []
    for p in sorted(base.glob(pattern)):
        if not p.is_file():
            continue
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        items.append(
            {
                "path": str(p),
                "category": category,
                "bytes": size,
                "ext": p.suffix.lower(),
            }
        )
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apps-root", default="")
    ap.add_argument(
        "--out",
        default="training_data/exploration_manifest.json",
    )
    args = ap.parse_args()
    root = Path(args.apps_root) if args.apps_root else apps_root()
    out = Path(args.out)
    if not out.is_absolute():
        out = Path(__file__).resolve().parent.parent / out

    eglab = ninefold_egregorelab(root)
    research = s2_research(root)
    marketing = s2_marketing_docs(root)
    forge = s2_forge_rag(root)

    items: list[dict] = []
    items += scan_glob(eglab / "podcasts", "*.json", "podcast_script_json")
    items += scan_glob(eglab / "podcasts", "*.md", "podcast_script_md")
    items += scan_glob(research, "SOLARPUNK*.md", "research_solarpunk")
    items += scan_glob(research / "canon", "**/*.md", "canon")
    items += scan_glob(research / "docs", "**/*.md", "research_docs")
    items += scan_glob(research / "discourse", "**/*", "discourse")
    items += scan_glob(marketing, "**/*.md", "marketing_docs")
    items += scan_glob(forge, "*.md", "forge_rag")

    ep01 = list(eglab.glob("**/episode_01_solarpunk*.json"))
    for p in ep01:
        items.append(
            {
                "path": str(p),
                "category": "episode_01_solarpunk",
                "bytes": p.stat().st_size if p.exists() else 0,
                "ext": ".json",
            }
        )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "apps_root": str(root),
        "counts": {},
        "items": items,
    }
    for it in items:
        c = it["category"]
        manifest["counts"][c] = manifest["counts"].get(c, 0) + 1
    manifest["total_files"] = len(items)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {out} ({manifest['total_files']} files)")
    for k, v in sorted(manifest["counts"].items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
