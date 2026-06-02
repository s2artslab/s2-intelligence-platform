#!/usr/bin/env python3
"""Smoke BitNet sidecar + gateway research infer (no billing)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def post(url: str, body: dict, headers: dict | None = None, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        url,
        json.dumps(body).encode(),
        {"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    sidecar = "http://127.0.0.1:8120/generate"
    gateway = "http://127.0.0.1:3020/api/research/bitnet/infer"
    prompt = "Summarize in one sentence: The court denied the motion without prejudice."

    print("=== BitNet sidecar direct ===")
    try:
        out = post(
            sidecar,
            {"prompt": prompt, "max_tokens": 80, "temperature": 0.2, "task_class": "summary"},
        )
        text = (out.get("response") or out.get("content") or "")[:200]
        print(f"OK  {text!r}")
    except Exception as e:
        print(f"FAIL sidecar: {e}")
        return 1

    print("\n=== Gateway research infer (compact lane) ===")
    try:
        out = post(
            gateway,
            {"text": prompt, "task_class": "summary", "max_tokens": 80, "context": "general"},
            headers={"X-S2-Inference-Lane": "compact"},
        )
        text = (out.get("content") or out.get("response") or "")[:200]
        print(f"OK  lane={out.get('lane')} bits={out.get('quantization_bits')} {text!r}")
    except Exception as e:
        print(f"FAIL gateway: {e}")
        return 1

    print("\nSMOKE PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
