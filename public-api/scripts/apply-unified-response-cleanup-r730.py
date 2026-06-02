#!/usr/bin/env python3
"""
Patch unified_egregore_service/app.py to strip canned openers from generated text.
Idempotent. Complements apply-unified-tier-c-prompt-format-r730.py (single-pattern strip).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MARKER = "def _clean_generated_response("
HELPER = '''

def _clean_generated_response(response: str) -> str:
    """Remove template opener sentences (train/serve quality gate alignment)."""
    text = (response or "").strip()
    if not text:
        return text
    patterns = [
        re.compile(r"^In the context of(?: \\w+)+,\\s*", re.I),
        re.compile(r"^From a \\w+ perspective,\\s*", re.I),
        re.compile(r"^In my view,\\s*", re.I),
        re.compile(r"^In one sentence, the art of integration[^.]{0,160}\\.\\s*", re.I),
        re.compile(r"^In the context of[^.]{0,160}\\.\\s*", re.I),
        re.compile(r"^From a \\w+ perspective,[^.]{0,160}\\.\\s*", re.I),
    ]
    for _ in range(3):
        changed = False
        for pat in patterns:
            new = pat.sub("", text, count=1).strip()
            if new != text and len(new) >= 40:
                text = new
                changed = True
                break
        if not changed:
            break
    return text

'''


SKIP_CALL = '''        skip_clean = (
            data.get("skip_response_cleanup") is True
            or str(data.get("skip_response_cleanup", "")).lower() in ("1", "true", "yes")
            or os.environ.get("EGREGORE_SKIP_RESPONSE_CLEANUP") == "1"
        )
        if not skip_clean:
            response = _clean_generated_response(response)'''

SKIP_OLD = "        response = _clean_generated_response(response)"


def patch_app(app_path: Path) -> bool:
    text = app_path.read_text(encoding="utf-8")
    changed = False
    if SKIP_OLD in text and "skip_response_cleanup" not in text:
        text = text.replace(SKIP_OLD, SKIP_CALL, 1)
        changed = True
        print("  patched skip_response_cleanup gate")
    if "import os" not in text.split("\n")[:25]:
        text = text.replace("import re\n", "import re\nimport os\n", 1)
        changed = True
    if changed:
        app_path.write_text(text, encoding="utf-8")
        return True

    if MARKER in text:
        # Re-patch patterns if helper exists but patterns are stale
        old_block = '''    patterns = [
        re.compile(r"^In the context of[^.]{0,160}\\.\\s*", re.I),
        re.compile(r"^From a \\w+ perspective,[^.]{0,160}\\.\\s*", re.I),
        re.compile(r"^In my view,[^.]{0,120}\\.\\s*", re.I),
        re.compile(
            r"^In one sentence, the art of integration[^.]{0,160}\\.\\s*", re.I
        ),
    ]'''
        new_block = '''    patterns = [
        re.compile(r"^In the context of(?: \\w+)+,\\s*", re.I),
        re.compile(r"^From a \\w+ perspective,\\s*", re.I),
        re.compile(r"^In my view,\\s*", re.I),
        re.compile(r"^In one sentence, the art of integration[^.]{0,160}\\.\\s*", re.I),
        re.compile(r"^In the context of[^.]{0,160}\\.\\s*", re.I),
        re.compile(r"^From a \\w+ perspective,[^.]{0,160}\\.\\s*", re.I),
    ]'''
        if old_block in text:
            text = text.replace(old_block, new_block, 1)
            app_path.write_text(text, encoding="utf-8")
            print(f"  updated patterns: {app_path}")
            return True
        print(f"  already patched: {app_path}")
        return False

    anchor = "CANNED_OPENER_RE = re.compile"
    if anchor not in text:
        text = text.replace(
            "import re\n",
            "import re\n\n"
            'CANNED_OPENER_RE = re.compile(r"^In the context of[^.]{0,80}\\.\\s*", re.I)\n',
            1,
        )

    insert_at = text.find("def _format_prompt(")
    if insert_at < 0:
        print("ERROR: could not locate _format_prompt", file=sys.stderr)
        return False
    text = text[:insert_at] + HELPER + text[insert_at:]

    old = (
        '        response = re.sub(r"^(?:\\d+:\\s*)+", "", response).strip()\n'
        '        response = CANNED_OPENER_RE.sub("", response).strip()'
    )
    new = (
        '        response = re.sub(r"^(?:\\d+:\\s*)+", "", response).strip()\n'
        '        response = CANNED_OPENER_RE.sub("", response).strip()\n'
        '        response = _clean_generated_response(response)'
    )
    if old in text:
        text = text.replace(old, new, 1)
    elif "response = _clean_generated_response(response)" not in text:
        text = text.replace(
            '        response = re.sub(r"^(?:\\d+:\\s*)+", "", response).strip()',
            '        response = re.sub(r"^(?:\\d+:\\s*)+", "", response).strip()\n'
            '        response = _clean_generated_response(response)',
            1,
        )

    app_path.write_text(text, encoding="utf-8")
    print(f"  patched: {app_path}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eg-dir", default="/opt/s2-ecosystem/egregore-training")
    args = ap.parse_args()
    app_path = Path(args.eg_dir) / "unified_egregore_service" / "app.py"
    if not app_path.is_file():
        print(f"Missing {app_path}", file=sys.stderr)
        return 1
    patch_app(app_path)
    print("Restart: systemctl restart unified-egregore.service")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
