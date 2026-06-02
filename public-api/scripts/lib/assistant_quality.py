"""
Shared heuristics for Ake training assistant text (Tier C/D/E).

Used by audit, dataset builders, and (optionally) weighted collators.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# Opener templates the LoRA over-learned (align with tier-c-eval-gate-r730.py)
CANNED_OPENER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("in_the_context_of", re.compile(r"^In the context of(?: \w+)+,\s*", re.I)),
    ("from_perspective", re.compile(r"^From a \w+ perspective,\s*", re.I)),
    ("in_my_view", re.compile(r"^In my view,\s*", re.I)),
    ("several_threads", re.compile(r"several threads converge in the discussion below", re.I)),
    ("one_line_of_thought", re.compile(r"one line of thought stresses:", re.I)),
    ("partial_view", re.compile(r"This partial view points toward", re.I)),
    ("deep_key_boilerplate", re.compile(r"^Deep Key opens the threshold when we treat", re.I)),
]

# Softer signals — down-weight, not always drop
WEAK_SIGNAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("consciousness_generic", re.compile(r"\bconsciousness (is|shapes)\b", re.I)),
    ("systems_thinking_boiler", re.compile(r"systems thinking sees the whole", re.I)),
    ("integration_frame", re.compile(r"larger frame the collective", re.I)),
]


@dataclass
class QualityReport:
    flags: list[str] = field(default_factory=list)
    score: float = 1.0  # 1.0 = keep full weight; 0.0 = drop

    @property
    def is_canned(self) -> bool:
        return any(
            f in self.flags
            for f in (
                "in_the_context_of",
                "from_perspective",
                "several_threads",
                "one_line_of_thought",
            )
        )

    @property
    def should_drop(self) -> bool:
        return self.score <= 0.0 or (
            self.is_canned and len(self.flags) >= 2
        )


def extract_assistant_text(row: dict[str, Any]) -> str:
    for key in ("completion", "ake_response", "assistant"):
        val = row.get(key)
        if val:
            text = str(val).strip()
            if text.startswith("Ake:"):
                text = text[4:].lstrip()
            return text
    return ""


def score_assistant(text: str) -> QualityReport:
    text = (text or "").strip()
    rep = QualityReport()
    if not text:
        rep.flags.append("empty")
        rep.score = 0.0
        return rep

    if len(text) < 40:
        rep.flags.append("too_short")
        rep.score = min(rep.score, 0.3)

    for name, pat in CANNED_OPENER_PATTERNS:
        if pat.search(text):
            rep.flags.append(name)

    for name, pat in WEAK_SIGNAL_PATTERNS:
        if pat.search(text):
            rep.flags.append(name)

    if "in_the_context_of" in rep.flags or "from_perspective" in rep.flags:
        rep.score = min(rep.score, 0.15)

    if "several_threads" in rep.flags:
        rep.score = min(rep.score, 0.1)

    if len(rep.flags) >= 3 and rep.is_canned:
        rep.score = 0.0

    if "too_short" in rep.flags and rep.is_canned:
        rep.score = 0.0

    return rep


def strip_canned_opener(text: str) -> str:
    """Remove first boilerplate sentence when a known opener is detected."""
    text = text.strip()
    if not text:
        return text

    # First sentence strip for known openers
    for _ in range(3):
        changed = False
        for _, pat in CANNED_OPENER_PATTERNS[:3]:
            m = pat.match(text)
            if not m:
                continue
            rest = text[m.end() :].lstrip(" ,.")
            if len(rest) >= 40:
                text = rest
                changed = True
                break
        if not changed:
            break
    return text


def row_with_cleaned_assistant(row: dict[str, Any], new_body: str) -> dict[str, Any]:
    out = dict(row)
    body = new_body.strip()
    if "assistant" in out or out.get("assistant"):
        out["assistant"] = f"Ake: {body}" if not body.startswith("Ake:") else body
    out["ake_response"] = body[4:].strip() if body.startswith("Ake:") else body
    return out
