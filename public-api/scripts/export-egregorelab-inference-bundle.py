#!/usr/bin/env python3
"""
Export EgregoreLab user egregores into BitNet 1.58-bit training bundles + inference manifest.

Reads unified_egregore_profiles.json, builds compact JSONL (same prompt shell as Ninefold BitNet),
updates egregore_inference_manifest.json. Run train-bitnet-custom-egregore-r730.sh per egregore
to produce LoRA adapters and register them for the gateway dual-lane router.

  python3 scripts/export-egregorelab-inference-bundle.py \\
    --profiles /path/to/unified_egregore_profiles.json \\
    --out-dir /opt/s2-ecosystem/egregore-training/training_data/bitnet_egregores \\
    --manifest /opt/s2-ecosystem/egregore-training/training_data/egregore_inference_manifest.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.ninefold_egregores import DESIGNATIONS, NINEFOLD_SPECIALISTS

CANON_SKIP = set(NINEFOLD_SPECIALISTS) | {"ake", "shasta", "s2", "s2_foundation"}


def normalize_id(raw: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", str(raw or "").strip().lower())


def operator_skip_ids() -> set[str]:
    raw = __import__("os").environ.get("OPERATOR_EGREGORE_SKIP", "shasta")
    return {normalize_id(x) for x in raw.split(",") if x.strip()}


def egregore_prompt(egregore: str, designation: str, question: str) -> str:
    cap = egregore.replace("_", " ").title()
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


def rows_from_pos_ex(eg_id: str, basic: dict, style_kernel: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    pos = list(style_kernel.get("pos_ex") or [])
    specialty = basic.get("specialty") or "guidance"
    templates = [
        "Give compact guidance on {specialty}.",
        "Speak in your authentic voice — one decisive line.",
        "What is your core stance on {specialty}?",
        "Reply as this egregore in under two sentences.",
    ]
    for i, line in enumerate(pos):
        tpl = templates[i % len(templates)]
        q = tpl.format(specialty=specialty)
        rows.append((q, line))
    return rows


def rows_from_memory(training_data: dict) -> list[tuple[str, str]]:
    """User-uploaded ChatGPT export on this egregore profile only (EgregoreLab opt-in)."""
    rows: list[tuple[str, str]] = []
    mem = training_data.get("chatgpt_memory") or {}
    for conv in mem.get("conversations") or []:
        if isinstance(conv, dict):
            user = (conv.get("user") or conv.get("prompt") or "").strip()
            assistant = (conv.get("assistant") or conv.get("response") or "").strip()
            if user and assistant:
                rows.append((user, assistant))
            continue
        if isinstance(conv, list):
            for turn in conv:
                if not isinstance(turn, dict):
                    continue
                role = str(turn.get("role") or "").lower()
                content = (turn.get("content") or turn.get("text") or "").strip()
                if role == "user" and content:
                    rows.append((content, ""))
                elif role in ("assistant", "egregore") and content and rows and not rows[-1][1]:
                    q = rows.pop()[0]
                    rows.append((q, content))
    return rows


def rows_from_traits(eg_id: str, basic: dict, personality: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    name = basic.get("name") or eg_id.title()
    specialty = basic.get("specialty") or "general guidance"
    traits = personality.get("traits") or []
    trait_str = ", ".join(traits[:4]) if traits else "present, clear"
    prompts = [
        f"Who are you and what is your specialty?",
        f"How do you approach {specialty}?",
        f"Describe your personality in one paragraph.",
        f"What makes your voice distinct?",
        f"A user asks for help with {specialty}. Respond briefly.",
    ]
    for q in prompts:
        a = (
            f"I am {name}. My specialty is {specialty}. "
            f"I am {trait_str}. I answer with clarity and stay true to my vessel."
        )
        rows.append((q, a))
    return rows


def build_rows(eg_id: str, profile: dict, target: int) -> list[tuple[str, str]]:
    basic = profile.get("basic") or {}
    personality = profile.get("personality") or {}
    style_kernel = profile.get("style_kernel") or {}
    training_data = profile.get("training_data") or {}

    pool: list[tuple[str, str]] = []
    pool.extend(rows_from_pos_ex(eg_id, basic, style_kernel))
    pool.extend(rows_from_memory(training_data))
    pool.extend(rows_from_traits(eg_id, basic, personality))

    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str]] = []
    for q, a in pool:
        key = (q.strip(), a.strip())
        if not q or not a or key in seen:
            continue
        seen.add(key)
        unique.append(key)

    if len(unique) >= target:
        return unique[:target]

    # Pad with paraphrased pos_ex if thin profile
    while len(unique) < target and style_kernel.get("pos_ex"):
        for line in style_kernel["pos_ex"]:
            q = f"Echo your voice: {line[:40]}…"
            unique.append((q, line))
            if len(unique) >= target:
                break
        if len(unique) < target:
            break

    return unique[:target]


def write_jsonl(
    eg_id: str,
    profile: dict,
    out_path: Path,
    target: int,
) -> int:
    basic = profile.get("basic") or {}
    designation = basic.get("designation") or basic.get("specialty") or eg_id.title()
    pairs = build_rows(eg_id, profile, target)
    written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for i, (q, resp) in enumerate(pairs):
            row = {
                "id": f"bitnet-{eg_id}-{i}",
                "egregore": eg_id,
                "prompt": egregore_prompt(eg_id, designation, q),
                "completion": trim_response(resp),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


def load_json(path: Path, fallback: dict) -> dict:
    if not path.is_file():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--profiles",
        default=str(
            Path(__file__).resolve().parents[3]
            / "ninefold-studio-clean"
            / "egregorelab"
            / "config"
            / "unified_egregore_profiles.json"
        ),
    )
    ap.add_argument(
        "--out-dir",
        default="/opt/s2-ecosystem/egregore-training/training_data/bitnet_egregores",
    )
    ap.add_argument(
        "--manifest",
        default="/opt/s2-ecosystem/egregore-training/training_data/egregore_inference_manifest.json",
    )
    ap.add_argument(
        "--registry",
        default="/opt/s2-ecosystem/egregore-training/training_data/bitnet_adapters/bitnet_egregore_registry.json",
    )
    ap.add_argument("--per-egregore", type=int, default=400)
    ap.add_argument("--egregore", default="", help="Single egregore id (default: all user-generated)")
    ap.add_argument("--include-canon", action="store_true", help="Also export Ninefold canon ids")
    ap.add_argument(
        "--allow-operator",
        action="store_true",
        help="Allow export of operator/internal ids (OPERATOR_EGREGORE_SKIP)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    profiles_path = Path(args.profiles)
    if not profiles_path.is_file():
        print(f"ERROR: profiles not found: {profiles_path}", file=sys.stderr)
        return 1

    data = json.loads(profiles_path.read_text(encoding="utf-8"))
    egregores = data.get("egregores") or {}
    out_dir = Path(args.out_dir)
    manifest_path = Path(args.manifest)
    registry_path = Path(args.registry)

    if args.egregore:
        ids = [normalize_id(args.egregore)]
    else:
        ids = sorted(
            eg
            for eg in egregores
            if args.include_canon or normalize_id(eg) not in CANON_SKIP
        )

    manifest = load_json(manifest_path, {"egregores": {}, "updated_at": None})
    manifest.setdefault("egregores", {})
    registry = load_json(registry_path, {})

    total = 0
    for raw_id in ids:
        eg_id = normalize_id(raw_id)
        profile = egregores.get(raw_id) or egregores.get(eg_id)
        if not profile:
            print(f"WARN skip {eg_id}: not in profiles", file=sys.stderr)
            continue
        if not args.include_canon and eg_id in CANON_SKIP:
            continue
        if eg_id in operator_skip_ids() and not (args.egregore and args.allow_operator):
            print(f"SKIP {eg_id}: operator/internal profile (use --allow-operator to override)", file=sys.stderr)
            continue

        out_path = out_dir / f"bitnet_{eg_id}.jsonl"
        adapter_path = registry_path.parent / f"bitnet_{eg_id}_lora.gguf"
        basic = profile.get("basic") or {}

        if args.dry_run:
            n = len(build_rows(eg_id, profile, args.per_egregore))
            print(f"DRY {eg_id}: would write {n} rows -> {out_path}")
            total += n
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        written = write_jsonl(eg_id, profile, out_path, args.per_egregore)
        total += written

        manifest["egregores"][eg_id] = {
            **manifest["egregores"].get(eg_id, {}),
            "egregore_id": eg_id,
            "name": basic.get("name") or eg_id,
            "designation": basic.get("designation") or "",
            "specialty": basic.get("specialty") or "",
            "source": "egregorelab" if eg_id not in CANON_SKIP else "ninefold",
            "bitnet_dataset": str(out_path),
            "bitnet_adapter": str(adapter_path) if adapter_path.is_file() else None,
            "training_rows": written,
            "lanes": {
                "hosted": True,
                "bitnet": adapter_path.is_file(),
            },
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if adapter_path.is_file():
            registry[eg_id] = str(adapter_path)

        print(f"{eg_id}: {written} rows -> {out_path}")

    if args.dry_run:
        print(f"Total rows (dry): {total}")
        return 0 if total else 1

    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest: {manifest_path}")

    if registry:
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
        print(f"Registry: {registry_path} ({len(registry)} adapters)")

    print(f"Done — {total} rows across {len(ids)} egregore(s)")
    if total:
        print("Next: bash scripts/train-bitnet-custom-egregore-r730.sh EGREGORE_ID=<id>")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
