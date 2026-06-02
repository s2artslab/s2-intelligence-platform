#!/usr/bin/env python3
"""
BitNet vs 4-bit baseline benchmark — records runs for S² Research.

  python3 scripts/bitnet-benchmark-r730.py
  python3 scripts/bitnet-benchmark-r730.py --gateway http://127.0.0.1:3020
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib.assistant_quality import score_assistant  # noqa: E402

SPECIALIST_PROMPTS = [
    {"id": "route-legal-general", "task_class": "routing", "text": "Classify: Is this a legal or general question? Question: How do I file a motion?"},
    {"id": "tag-urgency", "task_class": "tagging", "text": "Tag urgency (low/medium/high): Client needs response by tomorrow on contract review."},
    {"id": "summary-short", "task_class": "summary", "text": "Summarize in one sentence: The court denied the motion without prejudice and gave 14 days to amend."},
    {"id": "classify-intent", "task_class": "classification", "text": "Intent label only: User asks for step-by-step instructions to reset their password."},
    {"id": "compact-qa", "task_class": "compact", "text": "Answer in under 40 words: What is RAG in AI systems?"},
]


def post_json(url: str, body: dict, timeout: int, headers: dict | None = None) -> dict:
    data = json.dumps(body).encode()
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_json(url: str, timeout: int) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def run_lane(gateway: str, prompt: dict, lane: str, timeout: int) -> dict:
    headers = {}
    body = {
        "text": prompt["text"],
        "context": "general",
        "task_class": prompt["task_class"],
        "max_tokens": 120,
        "temperature": 0.2,
    }
    if lane == "bitnet":
        headers["X-S2-Inference-Lane"] = "compact"
        body["inference_lane"] = "bitnet"
    started = time.time()
    out = post_json(f"{gateway.rstrip('/')}/api/research/bitnet/infer", body, timeout, headers)
    latency = int((time.time() - started) * 1000)
    content = (out.get("content") or out.get("response") or "").strip()
    quality = score_assistant(content, user=prompt["text"])
    return {
        "lane": lane,
        "prompt_id": prompt["id"],
        "task_class": prompt["task_class"],
        "latency_ms": out.get("latency_ms") or latency,
        "quality_score": quality.score,
        "hallucination_flag": quality.score < 0.35,
        "response_preview": content[:400],
        "model_id": out.get("model") or "",
        "quantization_bits": out.get("quantization_bits"),
        "memory_mb": out.get("memory_mb"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="BitNet vs baseline benchmark")
    ap.add_argument("--gateway", default="http://127.0.0.1:3020")
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--prompts", type=int, default=len(SPECIALIST_PROMPTS))
    args = ap.parse_args()

    gateway = args.gateway.rstrip("/")
    try:
        status = get_json(f"{gateway}/api/research/bitnet/status", args.timeout)
    except urllib.error.URLError as e:
        print(f"FAIL: gateway research status unreachable: {e}", file=sys.stderr)
        return 1

    if not status.get("bitnet_enabled"):
        print("WARN: BITNET_ENABLED is false on gateway — enabling infer endpoint may still work in lab")

    results = []
    for prompt in SPECIALIST_PROMPTS[: args.prompts]:
        print(f"Prompt {prompt['id']}…")
        for lane in ("bitnet", "baseline"):
            try:
                row = run_lane(gateway, prompt, lane, args.timeout)
                results.append(row)
                print(f"  {lane}: latency={row['latency_ms']}ms quality={row['quality_score']:.2f}")
            except urllib.error.URLError as e:
                print(f"  {lane}: FAIL {e}", file=sys.stderr)
                results.append({"lane": lane, "prompt_id": prompt["id"], "error": str(e)})

    summary = post_json(
        f"{gateway}/api/research/bitnet/record-batch",
        {"runs": results, "run_type": "benchmark"},
        args.timeout,
    )
    print(json.dumps({"recorded": summary.get("recorded", 0), "results": results}, indent=2))
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
