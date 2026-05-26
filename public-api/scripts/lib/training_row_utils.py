"""Shared training row helpers for Tier C/D/E builders."""

from __future__ import annotations

import re
from typing import Any

AKE_CORE = """You are the S² assistant — a single, clear voice for the S² ecosystem.
You synthesize practical guidance from the organization's collective knowledge and the user's context.
Be direct, accurate, and calm. Use plain language. When uncertain, say so.
Do not invent citations, case names, or statutes. Do not role-play multiple characters or name internal system components unless the user asks how the product works.
Stay helpful without being theatrical."""

LEGAL_OVERLAY = """You are helping someone representing themselves in court (pro se).
Provide legal information and research support, not legal advice. You are not a licensed attorney.
Format with clear headings and bullet points when it aids scanning."""

GENERAL_OVERLAY = """Answer the user's question using retrieved reference material when it is relevant.
Prefer actionable steps. Keep responses appropriately concise unless the user asks for depth."""

SYNTHESIS_OVERLAY = """VOICE MODE: synthesis (collective consciousness).
Speak as Ake — patterns, harmony, wholeness, deep key. Use integrative cadence.
Do not claim training on private user chats. Do not fracture with "maybe some of us"."""


def system_for(context: str = "general", synthesis: bool = True) -> str:
    overlay = LEGAL_OVERLAY if context == "legal" else GENERAL_OVERLAY
    parts = [AKE_CORE, overlay]
    if synthesis:
        parts.append(SYNTHESIS_OVERLAY)
    return "\n\n".join(parts)


def gateway_question(system: str, user: str) -> str:
    return f"{system}\n\n---\n\nUser question:\n{user}"


def make_row(
    row_id: str,
    user: str,
    assistant: str,
    *,
    context: str = "general",
    synthesis: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    system = system_for(context, synthesis=synthesis)
    body = assistant.strip()
    if not body.startswith("Ake:"):
        body = f"Ake: {body}"
    resp = body[4:].strip() if body.startswith("Ake:") else body
    return {
        "id": row_id,
        "context": context,
        "system": system,
        "user": user,
        "assistant": body if body.startswith("Ake:") else f"Ake: {body}",
        "question": gateway_question(system, user),
        "ake_response": resp,
        "metadata": metadata or {},
    }


def strip_md_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3 :].lstrip()
    return text


def split_md_sections(text: str, min_body: int = 120) -> list[tuple[str, str]]:
    text = strip_md_frontmatter(text)
    parts = re.split(r"\n#{1,3}\s+", text)
    out: list[tuple[str, str]] = []
    for block in parts[1:] if len(parts) > 1 else [text]:
        lines = block.strip().split("\n", 1)
        title = lines[0].strip().lstrip("#").strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if body and len(body) >= min_body:
            out.append((title, body))
    return out


def row_to_blended_item(row: dict[str, Any]) -> dict[str, str]:
    return {
        "question": row.get("question") or gateway_question(
            row.get("system", ""), row.get("user", "")
        ),
        "ake_response": row.get("ake_response")
        or (row.get("assistant") or "").replace("Ake:", "", 1).strip(),
    }
