#!/usr/bin/env python3
"""
Build one SFT mega-blend JSON for sovereign Ake / S² voice training.

Combines foundation pool, tier C/D/E/F (or a pre-merged CDE file), optional legacy
blended rows, and DPO chosen responses into a single deduplicated dataset.

Merge rules (priority — higher wins on the same dedupe key)
-----------------------------------------------------------
  10  foundation_pool.json          response → ake_response (gateway-wrapped)
  20  ake_blended_dataset.json      optional (--include-legacy)
  30  Tier C cleaned                default: ake_tier_c_cleaned_v4.json
  35  Tier E                        default: ake_tier_c_ollama_distill.jsonl
  40  Tier D                        default: ake_tier_d_long_v4_clean.jsonl
  42  Pre-built CDE                 --tier-cde (replaces inline C/D/E/F sampling)
  45  Tier F                        default: ake_tier_f_egregore_synthesis.jsonl
 100  preferences/ake_dpo_dataset.json   chosen always wins

Dedupe key (two levels)
-----------------------
  identity_key = sha256(full question + response) — drop exact duplicates only
  conflict_key = normalized bare user question — used only for cross-layer priority:
    when a higher-priority layer adds a row, remove lower-priority rows with the same
    conflict_key. Tier rows with the same bare question but different responses are kept.
  DPO: removes all rows sharing the conflict_key, then inserts the chosen response.
Quality: optional --min-assistant-score filters non-DPO layers (lib.assistant_quality).

Tier C/D/E/F sampling (when --tier-cde is not set) matches build-tier-cde-merge.py:
  ~65% C, ~10% D, ~10% E, ~15% F (by row count target = len(Tier C) after filter).

Output: JSON array compatible with train_egregore_model_7b.py / train_egregore_on_foundation_7b.py
when TIER_C_BLENDED points at the output file.

Usage (r730 defaults):
  python3 scripts/build_s2_mega_blend.py \\
    --training-dir /opt/s2-ecosystem/egregore-training/training_data \\
    --out /opt/s2-ecosystem/egregore-training/training_data/s2_ake_mega_blend.json

  python3 scripts/build_s2_mega_blend.py --tier-cde training_data/ake_tier_cde_blended_v4.json

Install: copy to /opt/s2-ecosystem/public-api/scripts/ (or run from repo checkout).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.assistant_quality import extract_assistant_text, score_assistant
from lib.training_row_utils import make_row, row_to_blended_item

logger = logging.getLogger(__name__)

# Priority constants — documented merge order
PRIORITY_FOUNDATION = 10
PRIORITY_LEGACY = 20
PRIORITY_TIER_C = 30
PRIORITY_TIER_E = 35
PRIORITY_TIER_D = 40
PRIORITY_TIER_CDE = 42
PRIORITY_TIER_F = 45
PRIORITY_DPO = 100

USER_QUESTION_MARKER = "User question:\n"
DPO_PROMPT_RE = re.compile(r"^User:\s*(.+?)(?:\nAke:)?\s*$", re.DOTALL)


@dataclass
class MegaRow:
    id: str
    question: str
    ake_response: str
    source_layer: str
    priority: int
    dedupe_key: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_output(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "ake_response": self.ake_response,
            "source_layer": self.source_layer,
            "metadata": {
                **self.metadata,
                "dedupe_key": self.dedupe_key,
                "merge_priority": self.priority,
            },
        }


def load_json_array(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def normalize_dedupe_key(question: str) -> str:
    """Bare user question for collision detection across layers."""
    q = (question or "").strip()
    if USER_QUESTION_MARKER in q:
        q = q.split(USER_QUESTION_MARKER, 1)[1]
    if "---" in q and USER_QUESTION_MARKER not in (question or ""):
        # Gateway block before user section — keep full key if no marker
        pass
    q = q.split("\n---")[0].strip()
    q = q.replace("User: ", "", 1).strip()
    if "\nAke:" in q:
        q = q.split("\nAke:")[0].strip()
    return " ".join(q.lower().split())


def parse_dpo_prompt(prompt: str) -> str:
    prompt = (prompt or "").strip()
    m = DPO_PROMPT_RE.match(prompt)
    if m:
        return m.group(1).strip()
    if prompt.startswith("User: "):
        prompt = prompt[6:]
    if "\nAke:" in prompt:
        prompt = prompt.split("\nAke:")[0]
    return prompt.strip()


def passes_quality(item: dict[str, Any], min_score: float) -> bool:
    if min_score <= 0:
        return True
    rep = score_assistant(extract_assistant_text(item))
    return rep.score >= min_score and not rep.should_drop


def is_gateway_question(question: str) -> bool:
    return USER_QUESTION_MARKER in (question or "")


def wrap_short_question(
    row_id: str,
    question: str,
    response: str,
    *,
    context: str = "general",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize short User:/plain questions to Tier C gateway format."""
    q = question.strip()
    if q.startswith("User: "):
        q = q[6:].strip()
    if is_gateway_question(q):
        return {
            "id": row_id,
            "question": q,
            "ake_response": response.strip(),
            "metadata": metadata or {},
        }
    return make_row(
        row_id,
        q,
        response,
        context=context,
        synthesis=True,
        metadata=metadata or {},
    )


def row_from_blended_item(
    item: dict[str, Any],
    *,
    layer: str,
    priority: int,
    row_id: str | None = None,
    gateway_wrap: bool = False,
) -> MegaRow | None:
    question = (item.get("question") or "").strip()
    response = (
        item.get("ake_response")
        or item.get("response")
        or (item.get("assistant") or "").replace("Ake:", "", 1).strip()
    ).strip()
    if not question or not response:
        return None

    if gateway_wrap and not is_gateway_question(question):
        wrapped = wrap_short_question(
            row_id or item.get("id") or f"mega-{layer}-{hashlib.sha1(question.encode()).hexdigest()[:10]}",
            question,
            response,
            context=str(item.get("context") or "general"),
            metadata={"source_id": item.get("id"), **(item.get("metadata") or {})},
        )
        question = wrapped["question"]
        response = wrapped["ake_response"]
        row_id = wrapped["id"]
    else:
        row_id = row_id or item.get("id") or f"mega-{layer}-{hashlib.sha1(question.encode()).hexdigest()[:10]}"

    ck = conflict_key(question)
    if not ck:
        return None

    return MegaRow(
        id=str(row_id),
        question=question,
        ake_response=response,
        source_layer=layer,
        priority=priority,
        dedupe_key=ck,
        metadata={
            "source_id": item.get("id"),
            **(item.get("metadata") or {}),
        },
    )


def identity_key(question: str, response: str) -> str:
    payload = f"{question.strip()}\0{response.strip()}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def conflict_key(question: str) -> str:
    """Bare user question — cross-layer override only."""
    return normalize_dedupe_key(question)


@dataclass
class MegaBlendCollector:
    """Accumulates rows; identity-dedupes; bare-question overrides across layers."""

    rows: list[MegaRow] = field(default_factory=list)
    identities: set[str] = field(default_factory=set)
    by_conflict: dict[str, list[MegaRow]] = field(default_factory=dict)
    overrides: list[str] = field(default_factory=list)
    layer_counts: dict[str, int] = field(default_factory=dict)

    def _drop_conflict(self, ck: str, max_priority: int) -> None:
        victims = [r for r in self.by_conflict.get(ck, []) if r.priority < max_priority]
        if not victims:
            return
        victim_ids = {identity_key(r.question, r.ake_response) for r in victims}
        self.rows = [r for r in self.rows if identity_key(r.question, r.ake_response) not in victim_ids]
        self.identities -= victim_ids
        self.by_conflict[ck] = [r for r in self.by_conflict.get(ck, []) if r.priority >= max_priority]
        self.overrides.append(ck)

    def add(self, row: MegaRow | None, *, strip_lower: bool = True) -> bool:
        if row is None:
            return False
        ik = identity_key(row.question, row.ake_response)
        if ik in self.identities:
            return False
        if strip_lower:
            self._drop_conflict(row.dedupe_key, row.priority)
        self.rows.append(row)
        self.identities.add(ik)
        self.by_conflict.setdefault(row.dedupe_key, []).append(row)
        self.layer_counts[row.source_layer] = self.layer_counts.get(row.source_layer, 0) + 1
        return True

    def supersede_conflict(self, row: MegaRow | None) -> bool:
        """DPO: remove all rows with the same bare question, then insert."""
        if row is None:
            return False
        ck = row.dedupe_key
        victims = self.by_conflict.pop(ck, [])
        if victims:
            victim_ids = {identity_key(r.question, r.ake_response) for r in victims}
            self.rows = [r for r in self.rows if identity_key(r.question, r.ake_response) not in victim_ids]
            self.identities -= victim_ids
            self.overrides.append(ck)
        ik = identity_key(row.question, row.ake_response)
        if ik in self.identities:
            return False
        self.rows.append(row)
        self.identities.add(ik)
        self.by_conflict.setdefault(ck, []).append(row)
        self.layer_counts[row.source_layer] = self.layer_counts.get(row.source_layer, 0) + 1
        return True


def sample_tier_cde(
    tier_c: list[dict[str, Any]],
    tier_d: list[dict[str, Any]],
    tier_e: list[dict[str, Any]],
    tier_f: list[dict[str, Any]],
    *,
    seed: int,
    tier_c_ratio: float = 0.65,
    tier_d_ratio: float = 0.10,
    tier_e_ratio: float = 0.10,
    tier_f_ratio: float = 0.15,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Same count targets as build-tier-cde-merge.py."""
    random.seed(seed)
    total_target = len(tier_c)
    if total_target < 100:
        total_target = max(1000, len(tier_c) + len(tier_d) + len(tier_e))

    f_ratio = tier_f_ratio if tier_f else 0.0
    c_ratio = tier_c_ratio
    if not tier_f and f_ratio > 0:
        c_ratio += f_ratio
        f_ratio = 0.0

    n_c = int(total_target * c_ratio)
    n_d = int(total_target * tier_d_ratio)
    n_e = int(total_target * tier_e_ratio)
    n_f = int(total_target * f_ratio) if tier_f else 0

    if len(tier_c) >= n_c:
        c_sample = random.sample(tier_c, n_c) if n_c < len(tier_c) else list(tier_c)
    else:
        c_sample = list(tier_c)

    def sample_pool(pool: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
        if not pool:
            return []
        if n <= len(pool):
            return random.sample(pool, n)
        return pool + random.choices(pool, k=n - len(pool))

    merged = (
        c_sample
        + sample_pool(tier_d, n_d)
        + sample_pool(tier_e, n_e)
        + sample_pool(tier_f, n_f)
    )
    random.shuffle(merged)
    stats = {
        "tier_c_used": len(c_sample),
        "tier_d_used": min(n_d, len(tier_d)) if tier_d else 0,
        "tier_e_used": min(n_e, len(tier_e)) if tier_e else 0,
        "tier_f_used": min(n_f, len(tier_f)) if tier_f else 0,
        "cde_sample_total": len(merged),
    }
    return merged, stats


def load_tier_rows(
    path: Path | None,
    *,
    min_score: float,
    skip_needs_review: bool,
) -> list[dict[str, Any]]:
    if not path or not path.is_file():
        return []
    if path.suffix == ".jsonl":
        raw = load_jsonl(path)
        if skip_needs_review:
            raw = [r for r in raw if not (r.get("metadata") or {}).get("needs_review")]
        items = [row_to_blended_item(r) for r in raw]
    else:
        items = load_json_array(path)
    if min_score <= 0:
        return items
    return [i for i in items if passes_quality(i, min_score)]


def build_pool(args: argparse.Namespace) -> tuple[MegaBlendCollector, dict[str, Any]]:
    td = Path(args.training_dir)
    collector = MegaBlendCollector()
    stats: dict[str, Any] = {
        "layers": {},
        "tier_cde_inline": None,
    }

    min_score = args.min_assistant_score
    gateway_wrap = args.gateway_wrap_legacy

    # --- Foundation (priority 10) ---
    foundation_path = Path(args.foundation) if args.foundation else td / "foundation_pool.json"
    foundation_in = 0
    foundation_kept = 0
    if foundation_path.is_file():
        for idx, item in enumerate(load_json_array(foundation_path)):
            foundation_in += 1
            q = (item.get("question") or "").strip()
            r = (item.get("response") or "").strip()
            if not q or not r:
                continue
            wrapped = make_row(
                f"mega-foundation-{item.get('id', idx)}",
                q,
                r,
                context="general",
                synthesis=True,
                metadata={
                    "source_layer": "foundation",
                    "source_egregore": item.get("source_egregore"),
                    "source_dataset": item.get("source_dataset"),
                },
            )
            if min_score > 0 and not passes_quality(wrapped, min_score):
                continue
            if collector.add(
                row_from_blended_item(wrapped, layer="foundation", priority=PRIORITY_FOUNDATION),
                strip_lower=False,
            ):
                foundation_kept += 1
    stats["layers"]["foundation"] = {
        "path": str(foundation_path),
        "rows_in": foundation_in,
        "kept": foundation_kept,
    }

    # --- Legacy blended (priority 20) ---
    if args.include_legacy:
        legacy_path = Path(args.legacy) if args.legacy else td / "ake_blended_dataset.json"
        legacy_in = 0
        legacy_kept = 0
        if legacy_path.is_file():
            for item in load_json_array(legacy_path):
                legacy_in += 1
                if min_score > 0 and not passes_quality(item, min_score):
                    continue
                if collector.add(
                    row_from_blended_item(
                        item,
                        layer="legacy_blended",
                        priority=PRIORITY_LEGACY,
                        gateway_wrap=gateway_wrap,
                    ),
                ):
                    legacy_kept += 1
        stats["layers"]["legacy_blended"] = {
            "path": str(legacy_path),
            "rows_in": legacy_in,
            "kept": legacy_kept,
        }

    # --- Tier block: pre-built CDE or inline C/D/E/F ---
    if args.tier_cde:
        cde_path = Path(args.tier_cde)
        cde_in = 0
        cde_kept = 0
        if cde_path.is_file():
            for item in load_json_array(cde_path):
                cde_in += 1
                if min_score > 0 and not passes_quality(item, min_score):
                    continue
                if collector.add(
                    row_from_blended_item(
                        item,
                        layer="tier_cde",
                        priority=PRIORITY_TIER_CDE,
                    ),
                ):
                    cde_kept += 1
        stats["layers"]["tier_cde"] = {
            "path": str(cde_path),
            "rows_in": cde_in,
            "kept": cde_kept,
        }
    else:
        tier_c_path = Path(args.tier_c) if args.tier_c else td / "ake_tier_c_cleaned_v4.json"
        tier_d_path = Path(args.tier_d) if args.tier_d else td / "ake_tier_d_long_v4_clean.jsonl"
        tier_e_path = Path(args.tier_e) if args.tier_e else td / "ake_tier_c_ollama_distill.jsonl"
        tier_f_path = Path(args.tier_f) if args.tier_f else td / "ake_tier_f_egregore_synthesis.jsonl"

        tier_c = load_tier_rows(tier_c_path, min_score=min_score, skip_needs_review=False)
        tier_d = load_tier_rows(tier_d_path, min_score=min_score, skip_needs_review=False)
        tier_e = load_tier_rows(tier_e_path, min_score=min_score, skip_needs_review=args.skip_needs_review)
        tier_f = load_tier_rows(tier_f_path, min_score=min_score, skip_needs_review=False)

        c_keys = {id(x) for x in tier_c}
        e_keys = {id(x) for x in tier_e}
        d_keys = {id(x) for x in tier_d}
        f_keys = {id(x) for x in tier_f}

        cde_sample, tier_cde_stats = sample_tier_cde(
            tier_c,
            tier_d,
            tier_e,
            tier_f,
            seed=args.seed,
            tier_c_ratio=args.tier_c_ratio,
            tier_d_ratio=args.tier_d_ratio,
            tier_e_ratio=args.tier_e_ratio,
            tier_f_ratio=args.tier_f_ratio,
        )

        tier_kept = 0
        for item in cde_sample:
            oid = id(item)
            if oid in f_keys:
                layer, layer_pri = "tier_f", PRIORITY_TIER_F
            elif oid in d_keys:
                layer, layer_pri = "tier_d", PRIORITY_TIER_D
            elif oid in e_keys:
                layer, layer_pri = "tier_e", PRIORITY_TIER_E
            else:
                layer, layer_pri = "tier_c", PRIORITY_TIER_C
            if collector.add(
                row_from_blended_item(item, layer=layer, priority=layer_pri),
            ):
                tier_kept += 1

        stats["tier_cde_inline"] = {
            "tier_c_path": str(tier_c_path),
            "tier_d_path": str(tier_d_path),
            "tier_e_path": str(tier_e_path),
            "tier_f_path": str(tier_f_path),
            "tier_c_in": len(tier_c),
            "tier_d_in": len(tier_d),
            "tier_e_in": len(tier_e),
            "tier_f_in": len(tier_f),
            "kept": tier_kept,
            **tier_cde_stats,
        }

    # --- DPO chosen (priority 100) ---
    dpo_path = Path(args.dpo) if args.dpo else td / "preferences" / "ake_dpo_dataset.json"
    dpo_in = 0
    dpo_kept = 0
    if dpo_path.is_file():
        dpo_rows = load_json_array(dpo_path)
        for idx, item in enumerate(dpo_rows):
            dpo_in += 1
            bare_q = parse_dpo_prompt(item.get("prompt", ""))
            chosen = (item.get("chosen") or "").strip()
            if not bare_q or not chosen:
                continue
            if chosen.startswith("Ake:"):
                chosen = chosen[4:].strip()
            if args.dpo_gateway_wrap:
                wrapped = wrap_short_question(
                    f"mega-dpo-{idx:05d}",
                    bare_q,
                    chosen,
                    metadata={"source_layer": "dpo", "dpo_index": idx},
                )
                question = wrapped["question"]
                response = wrapped["ake_response"]
                row_id = wrapped["id"]
            else:
                question = f"User: {bare_q}"
                response = chosen
                row_id = f"mega-dpo-{idx:05d}"

            row = MegaRow(
                id=row_id,
                question=question,
                ake_response=response,
                source_layer="dpo",
                priority=PRIORITY_DPO,
                dedupe_key=conflict_key(bare_q),
                metadata={"dpo_index": idx, "rejected_preview": (item.get("rejected") or "")[:120]},
            )
            if collector.supersede_conflict(row):
                dpo_kept += 1
    stats["layers"]["dpo"] = {
        "path": str(dpo_path),
        "rows_in": dpo_in,
        "kept": dpo_kept,
        "conflict_supersedes": len(collector.overrides),
    }

    stats["dedupe_overrides"] = len(collector.overrides)
    stats["merged_total"] = len(collector.rows)
    stats["by_layer"] = dict(collector.layer_counts)

    return collector, stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Build S² Ake mega-blend SFT dataset")
    ap.add_argument(
        "--training-dir",
        default=os.environ.get(
            "EGREGORE_TRAINING_DATA",
            "/opt/s2-ecosystem/egregore-training/training_data",
        ),
        help="Default root for foundation/tier/dpo paths",
    )
    ap.add_argument("--foundation", default="", help="foundation_pool.json path")
    ap.add_argument("--legacy", default="", help="ake_blended_dataset.json path")
    ap.add_argument("--include-legacy", action="store_true", help="Include legacy ake_blended rows (p20)")
    ap.add_argument(
        "--tier-cde",
        default="",
        help="Pre-merged CDE JSON (skips inline tier C/D/E/F load)",
    )
    ap.add_argument("--tier-c", default="", help="Tier C cleaned JSON")
    ap.add_argument("--tier-d", default="", help="Tier D JSONL")
    ap.add_argument("--tier-e", default="", help="Tier E / distill JSONL")
    ap.add_argument("--tier-f", default="", help="Tier F JSONL")
    ap.add_argument("--dpo", default="", help="ake_dpo_dataset.json path")
    ap.add_argument(
        "--out",
        default="training_data/s2_ake_mega_blend.json",
        help="Output blended JSON array",
    )
    ap.add_argument(
        "--manifest-out",
        default="",
        help="Merge stats JSON (default: <out>.manifest.json)",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tier-c-ratio", type=float, default=0.65)
    ap.add_argument("--tier-d-ratio", type=float, default=0.10)
    ap.add_argument("--tier-e-ratio", type=float, default=0.10)
    ap.add_argument("--tier-f-ratio", type=float, default=0.15)
    ap.add_argument("--skip-needs-review", action="store_true")
    ap.add_argument(
        "--min-assistant-score",
        type=float,
        default=0.0,
        help="Drop rows below this quality score (non-DPO layers)",
    )
    ap.add_argument(
        "--gateway-wrap-legacy",
        action="store_true",
        help="Wrap short legacy blended questions in Tier C gateway format",
    )
    ap.add_argument(
        "--dpo-gateway-wrap",
        action="store_true",
        default=True,
        help="Wrap DPO rows in gateway format (default: on)",
    )
    ap.add_argument(
        "--no-dpo-gateway-wrap",
        action="store_false",
        dest="dpo_gateway_wrap",
        help="Keep DPO questions as bare User: lines",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    collector, stats = build_pool(args)
    rows = [row.to_output() for row in collector.rows]
    random.seed(args.seed)
    random.shuffle(rows)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest_path = Path(args.manifest_out) if args.manifest_out else out.with_suffix(".manifest.json")
    manifest = {
        "output": str(out.resolve()),
        "merge_rules": {
            "priority_order": [
                {"layer": "foundation", "priority": PRIORITY_FOUNDATION},
                {"layer": "legacy_blended", "priority": PRIORITY_LEGACY, "optional": True},
                {"layer": "tier_c", "priority": PRIORITY_TIER_C},
                {"layer": "tier_e", "priority": PRIORITY_TIER_E},
                {"layer": "tier_d", "priority": PRIORITY_TIER_D},
                {"layer": "tier_cde", "priority": PRIORITY_TIER_CDE, "optional": True},
                {"layer": "tier_f", "priority": PRIORITY_TIER_F},
                {"layer": "dpo", "priority": PRIORITY_DPO, "wins_conflicts": True},
            ],
            "dedupe_key": "identity: sha256(question+response); conflict: bare user question",
            "tier_cde_ratios": {
                "tier_c": args.tier_c_ratio,
                "tier_d": args.tier_d_ratio,
                "tier_e": args.tier_e_ratio,
                "tier_f": args.tier_f_ratio,
            },
        },
        "stats": stats,
        "train_hint": {
            "env": f"TIER_C_BLENDED={out.resolve()}",
            "script": "train_egregore_on_foundation_7b.py ake --qlora",
            "alt_script": "train_egregore_model_7b.py ake --model qwen --qlora",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"merged_total": len(rows), "manifest": str(manifest_path), "out": str(out)}, indent=2))
    print(f"Wrote {out} ({len(rows)} rows)")
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
