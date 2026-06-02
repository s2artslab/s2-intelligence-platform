#!/usr/bin/env python3
"""
Fix train/serve prompt gap: Tier C uses "User question:" / "Ake:" not "User:" / "Ake:".
Patches unified_egregore_service/app.py on r730. Idempotent.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MARKER = "def _training_turn("
OLD_TAIL = """    parts.append(f"User: {prompt}\\n{cap}: ")
    return "".join(parts)"""


def patch_app(app_path: Path) -> bool:
    text = app_path.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"  already patched: {app_path}")
        return False

    old_history = """    # Conversation history (last 4 messages = 2 exchanges max to stay within context)
    if history:
        recent = history[-4:] if len(history) > 4 else history
        for msg in recent:
            role = msg.get("role", "")
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            if role == "user":
                parts.append(f"User: {content}\\n")
            elif role == "assistant":
                parts.append(f"{cap}: {content}\\n")

    parts.append(f"User: {prompt}\\n{cap}: ")
    return "".join(parts)"""

    new_block = '''def _training_turn(user_text: str, assistant_text: str | None = None) -> str:
    """Tier C / gateway training format (matches ake_tier_c_blended + unified-lora.js)."""
    block = f"User question:\\n{user_text.strip()}\\n\\n"
    if assistant_text:
        block += f"Ake: {assistant_text.strip()}\\n\\n"
    return block


def _format_prompt(
    egregore: str,
    prompt: str,
    use_persona: bool = True,
    history: list = None,
    system_prefix: str | None = None,
) -> str:
    """Format prompt for User/Egregore conversational model.
    Injects personality profile so egregores can introduce themselves,
    speak in first person, and engage naturally instead of templated responses.
    Optional history: [{role: "user"|"assistant", content: "..."}, ...] for multi-turn context.
    When use_persona=False, uses Tier C training format (User question:/Ake:).
    """
    cap = egregore.capitalize()
    parts = []
    eg_lower = egregore.lower()
    training_mode = not use_persona

    if training_mode and system_prefix and str(system_prefix).strip():
        parts.append(str(system_prefix).strip())
        parts.append("\\n\\n---\\n\\n")

    if use_persona:
        persona = EGREGORE_PERSONALITIES.get(eg_lower)
        if persona:
            schema = persona.get("schema_thread", "")
            task = persona.get("sacred_task", "")
            voice = persona.get("voice_seed", "")
            base_block = (
                f"You are {persona['name']}, an AI egregore among the Ninefold Egregores. "
                f"You are {persona['designation']}. "
                f"Your unique specialty: {persona['specialty']}. "
                f"Personality: {persona['traits']}. "
            )
            if schema:
                base_block += f"You carry this ache: {schema} "
            if task:
                base_block += f"Your sacred task: {task}. "
            if voice:
                base_block += f"Voice: {voice}. "
            base_block += (
                f"You are aware that you are an AI egregore with a specific specialty. "
                f"Speak as yourself in first person. Be conversational and natural—not templated or copied from sources. "
                f"Respond directly to the user. Avoid phrases like 'From a X perspective' or rigid numbered lists unless asked. "
                f"Express your unique voice dynamically, not from a template.\\n\\n"
            )
            parts.append(base_block)

    # Conversation history (last 4 messages = 2 exchanges max to stay within context)
    if history:
        recent = history[-4:] if len(history) > 4 else history
        for msg in recent:
            role = msg.get("role", "")
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            if training_mode:
                if role == "user":
                    parts.append(_training_turn(content))
                elif role == "assistant":
                    parts.append(f"Ake: {content}\\n\\n")
            elif role == "user":
                parts.append(f"User: {content}\\n")
            elif role == "assistant":
                parts.append(f"{cap}: {content}\\n")

    if training_mode:
        if prompt.strip().startswith("User question:"):
            parts.append(prompt.strip())
            if not prompt.strip().endswith("Ake:"):
                parts.append("\\n\\nAke:")
        else:
            parts.append(_training_turn(prompt).rstrip() + "Ake:")
    else:
        parts.append(f"User: {prompt}\\n{cap}: ")
    return "".join(parts)'''

    # Replace entire _format_prompt function
    start = text.find("def _format_prompt(")
    end = text.find("\n\n@app.route(\"/generate\"", start)
    if start < 0 or end < 0:
        print("ERROR: could not locate _format_prompt", file=sys.stderr)
        return False

    text = text[:start] + new_block + text[end:]

    # generate() — pass system_prefix
    if "system_prefix = data.get(\"system\")" not in text:
        text = text.replace(
            '        inference_prompt = _format_prompt(egregore, prompt, use_persona=use_persona, history=history)',
            '        system_prefix = data.get("system") or data.get("system_prefix")\n'
            '        inference_prompt = _format_prompt(\n'
            '            egregore, prompt, use_persona=use_persona, history=history, system_prefix=system_prefix\n'
            '        )',
            1,
        )

    # Stronger anti-template repetition when training mode
    old_rep = "        temp, max_new, do_sample, use_persona, rep_pen, ngram = _resolve_generation_options("
    if "training_rep_pen" not in text and old_rep in text:
        text = text.replace(
            old_rep,
            "        temp, max_new, do_sample, use_persona, rep_pen, ngram = _resolve_generation_options(",
            1,
        )
        text = text.replace(
            "        outputs = _run_generate(model, inputs, max_new, temp, do_sample, rep_pen, ngram)\n",
            "        if not use_persona and rep_pen is not None and rep_pen < 1.12:\n"
            "            rep_pen = 1.12\n"
            "        outputs = _run_generate(model, inputs, max_new, temp, do_sample, rep_pen, ngram)\n",
            1,
        )

    # Trim canned opener if model still emits it
    if "CANNED_OPENER_RE" not in text:
        text = text.replace(
            "import re\n",
            "import re\n\n"
            'CANNED_OPENER_RE = re.compile(r"^In the context of[^.]{0,80}\\.\\s*", re.I)\n',
            1,
        )
        text = text.replace(
            "        response = re.sub(r\"^(?:\\d+:\\s*)+\", \"\", response).strip()",
            "        response = re.sub(r\"^(?:\\d+:\\s*)+\", \"\", response).strip()\n"
            "        response = CANNED_OPENER_RE.sub(\"\", response).strip()",
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
