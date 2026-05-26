#!/usr/bin/env python3
"""
Build Tier E exploration training JSONL from podcasts, research, marketing, forge RAG.

  python3 scripts/build-tier-e-exploration.py \\
    --out training_data/ake_tier_e_exploration.jsonl \\
    --review-out training_data/tier_e_human_review.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.corpus_paths import (
    apps_root,
    ninefold_egregorelab,
    s2_forge_rag,
    s2_marketing_docs,
    s2_research,
)
from lib.training_row_utils import make_row, split_md_sections, strip_md_frontmatter


def synthesize_from_snippets(title: str, topic: str, snippets: list[str]) -> str:
    """Rule-based Ake synthesis draft — flag for human review."""
    parts = []
    parts.append(
        f"In my view, the collective held {title} as a field question — "
        f"not a slogan, but a design problem for how we relate, build, and regenerate."
    )
    if topic:
        parts.append(f"In the context of {topic}, several threads converge in the discussion below.")
    for i, snip in enumerate(snippets[:4]):
        s = re.sub(r"\s+", " ", snip.strip())[:280]
        if s:
            parts.append(
                f"From a synthesis perspective, one line of thought stresses: {s} "
                "This partial view points toward a larger frame the field can integrate."
            )
    parts.append(
        "Deep Key opens the threshold when we treat this topic as practice — "
        "what we build next must honor community, evidence, and regenerative intent."
    )
    return "\n\n".join(parts)


def load_podcast_json(path: Path) -> tuple[str, str, list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    title = (
        data.get("title")
        or data.get("episode_info", {}).get("title")
        or path.stem
    )
    topic = data.get("topic") or data.get("episode_info", {}).get("topic") or path.stem
    snippets: list[str] = []
    for seg in data.get("segments", []):
        text = (seg.get("text") or seg.get("content") or "").strip()
        if len(text) > 40:
            snippets.append(text)
    return str(title), str(topic), snippets


def episode_01_from_py(apps: Path) -> tuple[str, str, list[str]] | None:
    py_path = ninefold_egregorelab(apps) / "scripts" / "create_episode_01_solarpunk.py"
    if not py_path.is_file():
        return None
    text = py_path.read_text(encoding="utf-8")
    snippets = []
    for m in re.finditer(r'"([a-z]+)":\s*"([^"]{80,})"', text):
        if m.group(1) in ("rhys", "seraphel", "flux", "chalyth", "vireon"):
            snippets.append(m.group(2).replace("\\n", " "))
    return (
        "Solarpunk Movement: AI Perspectives on Regenerative Futures",
        "solarpunk_movement",
        snippets[:25],
    )


def add_podcasts(rows: list, review: list, apps: Path, max_episodes: int) -> int:
    n = 0
    pod_dir = ninefold_egregorelab(apps) / "podcasts"
    seen = set()
    ep01 = episode_01_from_py(apps)
    if ep01:
        title, topic, snippets = ep01
        key = "episode_01_solarpunk"
        if key not in seen and snippets:
            seen.add(key)
            user = (
                f"Synthesize the Ninefold collective's exploration of {title}. "
                "Integrate as Ake; do not role-play individual egregores."
            )
            body = synthesize_from_snippets(title, topic, snippets)
            row = make_row(
                "ake-tiere-ep01-solarpunk",
                user,
                body,
                metadata={
                    "source": "podcast_synthesis",
                    "episode": "01",
                    "topic": topic,
                    "needs_review": True,
                    "provenance": "create_episode_01_solarpunk.py",
                },
            )
            rows.append(row)
            review.append((row["id"], title, body[:400]))
            n += 1

    if pod_dir.is_dir():
        files = sorted(pod_dir.glob("*.json"))[:max_episodes]
        for path in files:
            if path.stem in seen:
                continue
            try:
                title, topic, snippets = load_podcast_json(path)
            except (json.JSONDecodeError, OSError):
                continue
            if len(snippets) < 3:
                continue
            seen.add(path.stem)
            user = (
                f"Synthesize what the collective explored in '{title}'. "
                "Speak as Ake — one integrative voice, not eight separate speakers."
            )
            body = synthesize_from_snippets(title, topic, snippets)
            row = make_row(
                f"ake-tiere-pod-{path.stem[:40]}",
                user,
                body,
                metadata={
                    "source": "podcast_synthesis",
                    "file": str(path),
                    "needs_review": True,
                    "segment_count": len(snippets),
                },
            )
            rows.append(row)
            review.append((row["id"], title, body[:400]))
            n += 1
    return n


def add_research_md(rows: list, apps: Path, pattern: str, prefix: str, max_sections: int) -> int:
    n = 0
    research = s2_research(apps)
    for path in sorted(research.glob(pattern)):
        if not path.is_file():
            continue
        for i, (title, body) in enumerate(split_md_sections(path.read_text(encoding="utf-8"))):
            if i >= max_sections:
                break
            user = f"Explain '{title}' in the Ninefold / solarpunk research frame as Ake."
            rows.append(
                make_row(
                    f"{prefix}-{path.stem[:20]}-{i:03d}",
                    user,
                    body[:4000],
                    metadata={"source": "research_doc", "file": str(path), "section": title},
                )
            )
            n += 1
    return n


def add_canon(rows: list, apps: Path, max_files: int) -> int:
    n = 0
    canon = s2_research(apps) / "canon"
    if not canon.is_dir():
        return 0
    for path in sorted(canon.glob("**/*.md"))[:max_files]:
        body = strip_md_frontmatter(path.read_text(encoding="utf-8"))[:2500]
        if len(body) < 80:
            continue
        title = path.stem.replace("-", " ")
        user = f"What does Ninefold canon teach about {title}? Answer as Ake with calm precision."
        rows.append(
            make_row(
                f"ake-tiere-canon-{path.stem[:30]}",
                user,
                body,
                metadata={"source": "canon", "file": str(path), "needs_review": False},
            )
        )
        n += 1
    return n


def add_marketing_voice(rows: list, apps: Path) -> int:
    n = 0
    docs = s2_marketing_docs(apps)
    for name in (
        "BRAND_VOICE_AKE.md",
        "AKE_MESSAGING_CONTINUITY.md",
        "CLAIMS_REGISTER.md",
    ):
        path = docs / name
        if not path.is_file():
            continue
        body = strip_md_frontmatter(path.read_text(encoding="utf-8"))[:3500]
        user = (
            "How should the S² assistant speak in public marketing contexts? "
            "Summarize rules and boundaries as Ake."
        )
        rows.append(
            make_row(
                f"ake-tiere-mkt-{path.stem[:24]}",
                user,
                body,
                metadata={"source": "marketing_docs", "file": str(path)},
            )
        )
        n += 1
    return n


def add_forge_rag(rows: list, apps: Path) -> int:
    n = 0
    sp = s2_forge_rag(apps) / "solarpunk-community-campaign.md"
    if not sp.is_file():
        return 0
    body = strip_md_frontmatter(sp.read_text(encoding="utf-8"))
    user = "Synthesize the solarpunk IRL campaign posture for the S² field — real rooms, surplus, collectives."
    rows.append(
        make_row(
            "ake-tiere-forge-solarpunk-campaign",
            user,
            body,
            metadata={"source": "forge_rag", "file": str(sp)},
        )
    )
    return 1


def write_review(path: Path, review: list[tuple[str, str, str]]) -> None:
    lines = [
        "# Tier E — human review queue",
        "",
        "Approve or edit `ake_response` bodies before merge/retrain. "
        "Rows with `needs_review: true` are rule-based podcast syntheses.",
        "",
    ]
    for rid, title, preview in review:
        lines.append(f"## {rid}")
        lines.append(f"**Source:** {title}")
        lines.append("")
        lines.append(preview + "…")
        lines.append("")
        lines.append("---")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apps-root", default="")
    ap.add_argument("--out", default="training_data/ake_tier_e_exploration.jsonl")
    ap.add_argument("--review-out", default="training_data/tier_e_human_review.md")
    ap.add_argument("--max-podcast-json", type=int, default=30)
    ap.add_argument("--max-solarpunk-sections", type=int, default=12)
    ap.add_argument("--max-canon", type=int, default=40)
    args = ap.parse_args()

    apps = Path(args.apps_root) if args.apps_root else apps_root()
    out = Path(args.out)
    if not out.is_absolute():
        out = Path(__file__).resolve().parent.parent / out
    review_out = Path(args.review_out)
    if not review_out.is_absolute():
        review_out = Path(__file__).resolve().parent.parent / review_out

    rows: list = []
    review: list = []

    stats = {}
    stats["podcast"] = add_podcasts(rows, review, apps, args.max_podcast_json)
    stats["solarpunk_ecosystem"] = add_research_md(
        rows, apps, "SOLARPUNK*.md", "ake-tiere-sp", args.max_solarpunk_sections
    )
    stats["canon"] = add_canon(rows, apps, args.max_canon)
    stats["marketing"] = add_marketing_voice(rows, apps)
    stats["forge"] = add_forge_rag(rows, apps)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_review(review_out, review)
    print(f"Wrote {len(rows)} rows to {out}")
    print(f"Review pack: {review_out} ({len(review)} podcast syntheses)")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
