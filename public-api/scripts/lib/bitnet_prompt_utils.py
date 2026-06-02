"""Compact specialist prompt shells for BitNet train/serve alignment."""

from __future__ import annotations

TASK_INSTRUCTIONS: dict[str, str] = {
    "routing": "Reply with exactly one word: legal or general.",
    "tagging": "Reply with exactly one word: low, medium, or high.",
    "summary": "Reply with one concise sentence only.",
    "classification": "Reply with a short intent label (1-3 words).",
    "compact": "Reply in under 40 words.",
    "cheap_qa": "Reply in one short sentence.",
}


def specialist_user_prompt(task_class: str, user: str) -> str:
    task = (task_class or "compact").strip().lower()
    rule = TASK_INSTRUCTIONS.get(task, TASK_INSTRUCTIONS["compact"])
    body = user.strip()
    return f"Task: {task}\n{rule}\n\nInput: {body}\n\nOutput:"


def to_llamacpp_row(task_class: str, user: str, completion: str) -> dict[str, str]:
    return {
        "prompt": specialist_user_prompt(task_class, user),
        "completion": completion.strip(),
    }
