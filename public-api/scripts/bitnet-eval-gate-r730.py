#!/usr/bin/env python3
"""
BitNet specialist lane eval gate — exit 0 when compact tasks meet minimum quality.

  python3 scripts/bitnet-eval-gate-r730.py
  python3 scripts/bitnet-eval-gate-r730.py --gateway http://127.0.0.1:3020
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

MIN_QUALITY = 0.45
MAX_LATENCY_MS = 30000


def get_json(url: str, timeout: int) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gateway", default="http://127.0.0.1:3020")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--min-quality", type=float, default=MIN_QUALITY)
    args = ap.parse_args()

    gateway = args.gateway.rstrip("/")
    failures = []

    try:
        status = get_json(f"{gateway}/api/research/bitnet/status", args.timeout)
    except urllib.error.URLError as e:
        print(f"FAIL: cannot reach research status: {e}")
        return 1

    health = status.get("bitnet_health") or {}
    if not status.get("bitnet_enabled"):
        failures.append("BITNET_ENABLED is false")
    if not health.get("ok"):
        failures.append(f"bitnet sidecar unhealthy: {health.get('error') or health}")

    summary = status.get("summary") or {}
    bitnet_runs = summary.get("bitnet_runs") or 0
    if bitnet_runs < 1:
        failures.append("no bitnet benchmark runs recorded — run bitnet-benchmark-r730.py first")

    avg_q = summary.get("avg_bitnet_quality")
    if avg_q is not None and avg_q < args.min_quality:
        failures.append(f"avg_bitnet_quality {avg_q:.2f} < {args.min_quality}")

    avg_lat = summary.get("avg_bitnet_latency_ms")
    if avg_lat is not None and avg_lat > MAX_LATENCY_MS:
        failures.append(f"avg_bitnet_latency_ms {avg_lat:.0f} > {MAX_LATENCY_MS}")

    if failures:
        print("BitNet eval gate FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("BitNet eval gate PASSED")
    print(json.dumps({"summary": summary, "health": health}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
