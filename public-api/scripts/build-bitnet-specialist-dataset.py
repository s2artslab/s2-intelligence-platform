#!/usr/bin/env python3
"""
Build BitNet specialist JSONL via Ollama teacher (compact tasks, no Ake synthesis overlay).

Output formats:
  --format llamacpp  → {"prompt","completion"} for llama-finetune-lora / QVAC Fabric
  --format chat      → {"messages":[...]} for HF-style tooling

Usage:
  python3 scripts/build-bitnet-specialist-dataset.py \\
    --prompts training_data/bitnet-specialist-prompts.json \\
    --out /opt/s2-ecosystem/egregore-training/training_data/bitnet_specialist.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.bitnet_prompt_utils import specialist_user_prompt, to_llamacpp_row


def ollama_chat(base: str, model: str, user: str, timeout: int, max_words: int) -> str:
    system = (
        "You are a compact specialist assistant. Follow the task instruction exactly. "
        "Be brief. No preamble, no markdown headers, no role-play."
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": max_words * 4},
    }
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/chat",
        json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    return (data.get("message") or {}).get("content", "").strip()


def trim_completion(text: str, task_class: str) -> str:
    text = text.strip().split("\n")[0].strip()
    if task_class == "routing":
        low = text.lower()
        for word in ("legal", "general"):
            if word in low:
                return word
    if task_class == "tagging":
        low = text.lower()
        for word in ("low", "medium", "high"):
            if word in low:
                return word
    words = text.split()
    caps = {"compact": 40, "cheap_qa": 25, "summary": 35, "classification": 6, "routing": 1, "tagging": 1}
    limit = caps.get(task_class, 40)
    if len(words) > limit:
        text = " ".join(words[:limit])
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--model", default="s2-ake")
    ap.add_argument("--format", choices=("llamacpp", "chat"), default="llamacpp")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.5)
    args = ap.parse_args()

    prompts = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    if args.limit > 0:
        prompts = prompts[: args.limit]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with out_path.open("w", encoding="utf-8") as f:
        for item in prompts:
            task_class = item.get("task_class") or "compact"
            user = item.get("user") or item.get("text") or ""
            if not user:
                continue
            try:
                teacher_user = user
                completion = ollama_chat(
                    args.ollama_url, args.model, teacher_user, args.timeout, max_words=40
                )
            except (urllib.error.URLError, TimeoutError) as exc:
                print(f"WARN skip {item.get('id')}: {exc}", file=sys.stderr)
                continue
            completion = trim_completion(completion, task_class)
            if not completion:
                continue

            if args.format == "chat":
                row = {
                    "id": item.get("id"),
                    "task_class": task_class,
                    "messages": [
                        {"role": "user", "content": specialist_user_prompt(task_class, user)},
                        {"role": "assistant", "content": completion},
                    ],
                    "metadata": {"source": "ollama_distill", "teacher": args.model},
                }
            else:
                row = to_llamacpp_row(task_class, user, completion)
                row["id"] = item.get("id")
                row["task_class"] = task_class

            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
            print(f"OK {item.get('id')} → {completion[:60]!r}")
            time.sleep(args.sleep)

    print(f"Wrote {written} rows to {out_path}")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
