"""
Structured outputs for communication / digital media strategy workflows.
Used by API gateway `/v1/comm/templates` and `/v1/comm/fill` (no router required).
"""

from __future__ import annotations

from typing import Any, Dict

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "beat_sheet": {
        "title": "TV / digital beat sheet",
        "sections": [
            {"id": "slug", "label": "Slug / working title", "placeholder": ""},
            {"id": "nut", "label": "Nut graf (why now)", "placeholder": ""},
            {"id": "acts", "label": "Act breaks / blocks", "placeholder": "Act1 -> Act2 -> ..."},
            {"id": "sources", "label": "Primary sources", "placeholder": "Name + contact / doc"},
            {"id": "sot", "label": "SOT / standup plan", "placeholder": ""},
            {"id": "web", "label": "Digital extensions", "placeholder": "Shorts, thread, newsletter"},
        ],
    },
    "press_kit": {
        "title": "Press kit one-pager",
        "sections": [
            {"id": "boiler", "label": "Org boilerplate (50–80 words)", "placeholder": ""},
            {"id": "contacts", "label": "Media contacts", "placeholder": "Name, email, TZ, languages"},
            {"id": "facts", "label": "Key facts (bullets)", "placeholder": ""},
            {"id": "quotes", "label": "Approved quotes", "placeholder": "Speaker + context"},
            {"id": "logos", "label": "Asset links", "placeholder": "Logo pack, product shots"},
        ],
    },
    "methods_appendix": {
        "title": "Methods appendix (client memo)",
        "sections": [
            {"id": "question", "label": "Research question", "placeholder": ""},
            {"id": "design", "label": "Design / data collection", "placeholder": "Window, platform, sample"},
            {"id": "metrics", "label": "Metrics & definitions", "placeholder": ""},
            {"id": "limits", "label": "Limitations & ethics", "placeholder": "ToS, consent, IRB"},
            {"id": "repro", "label": "Reproducibility", "placeholder": "Hashes, seeds, version IDs"},
        ],
    },
}


def list_template_ids() -> list:
    return list(TEMPLATES.keys())


def fill_template(template_id: str, values: Dict[str, str]) -> str:
    t = TEMPLATES.get(template_id)
    if not t:
        raise KeyError(f"Unknown template: {template_id}")
    lines = [f"# {t['title']}", ""]
    for sec in t["sections"]:
        sid = sec["id"]
        val = values.get(sid) or sec.get("placeholder") or "_(fill)_"
        lines.append(f"## {sec['label']}")
        lines.append("")
        lines.append(str(val).strip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
