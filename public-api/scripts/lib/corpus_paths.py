"""Default paths for exploration / training corpus builders (override with --apps-root)."""

from __future__ import annotations

import os
from pathlib import Path


def apps_root() -> Path:
    env = os.environ.get("S2_APPS_ROOT", "").strip()
    if env:
        return Path(env)
    # APPs/s2-intelligence-platform/public-api/scripts/lib
    return Path(__file__).resolve().parents[4]


def ninefold_egregorelab(root: Path | None = None) -> Path:
    return (root or apps_root()) / "ninefold-studio-clean" / "egregorelab"


def s2_research(root: Path | None = None) -> Path:
    return (root or apps_root()) / "s2-research"


def s2_marketing_docs(root: Path | None = None) -> Path:
    return (root or apps_root()) / "S2 Marketing Automation" / "s2-marketing" / "docs"


def s2_forge_rag(root: Path | None = None) -> Path:
    return (root or apps_root()) / "s2forge" / "web" / "rag-corpus"


def public_api(root: Path | None = None) -> Path:
    if root:
        return root / "s2-intelligence-platform" / "public-api"
    return Path(__file__).resolve().parents[2]
