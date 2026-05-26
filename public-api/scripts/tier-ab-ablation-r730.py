#!/usr/bin/env python3
"""
Tier A/B ablation on r730 — run on host after patching unified service.
Tests prompt/decoding (Tier A) and adapter load modes (Tier B).
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("UNIFIED_URL", "http://127.0.0.1:8100")
QUESTIONS = [
    "Say hello in one short sentence as Ake.",
    "What is 2+2?",
    "In one sentence, what is a motion to dismiss?",
]


def post_generate(payload, timeout=300):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"status": "error", "message": e.read().decode()[:500]}


def restart_unified(env_extra: dict):
    lines = ["systemctl restart unified-egregore.service"]
    dropin = "/etc/systemd/system/unified-egregore.service.d/tier-ab.conf"
    content = "[Service]\n"
    for k, v in env_extra.items():
        content += f"Environment={k}={v}\n"
    with open(dropin, "w") as f:
        f.write(content)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "restart", "unified-egregore.service"], check=True)
    for _ in range(40):
        try:
            urllib.request.urlopen(f"{BASE}/health", timeout=3)
            break
        except Exception:
            time.sleep(3)
    # clear loaded models by restart — first call per mode loads fresh
    time.sleep(2)


def run_case(name, env_extra, gen_payload):
    print("\n" + "=" * 70)
    print("CASE:", name)
    print("ENV:", env_extra)
    restart_unified(env_extra)
    for q in QUESTIONS:
        p = {**gen_payload, "prompt": q}
        t0 = time.time()
        out = post_generate(p)
        dt = time.time() - t0
        resp = (out.get("response") or out.get("message") or "")[:280]
        print(f"  Q: {q[:50]}...")
        print(f"  ({dt:.1f}s) {resp}")
        print()


def main():
    # Tier A — training format, greedy, no persona
    run_case(
        "tier_a_training_greedy",
        {
            "EGREGORE_USE_PERSONA": "0",
            "EGREGORE_DO_SAMPLE": "0",
            "EGREGORE_DEFAULT_TEMPERATURE": "0.2",
            "EGREGORE_MAX_NEW_TOKENS": "120",
            "EGREGORE_ADAPTER_LOAD_MODE": "egregore_only",
        },
        {
            "egregore": "ake",
            "use_persona": False,
            "max_length": 120,
            "temperature": 0.2,
            "do_sample": False,
        },
    )

    # Tier B load modes (same Tier A decoding)
    for mode in ("egregore_only", "merge_foundation", "foundation_merged"):
        run_case(
            f"tier_b_load_{mode}",
            {
                "EGREGORE_USE_PERSONA": "0",
                "EGREGORE_DO_SAMPLE": "0",
                "EGREGORE_ADAPTER_LOAD_MODE": mode,
            },
            {"egregore": "ake", "use_persona": False, "max_length": 120, "do_sample": False},
        )

    print("\nAblation complete. Pick mode with most coherent answers.")


if __name__ == "__main__":
    main()
