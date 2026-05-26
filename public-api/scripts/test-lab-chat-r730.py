#!/usr/bin/env python3
import json
import time
import urllib.error
import urllib.request

def post(url, body, timeout=300):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read().decode()
        return r.status, time.time() - t0, data


if __name__ == "__main__":
    health = urllib.request.urlopen("http://127.0.0.1:3020/api/lab/unified-lora/health", timeout=30)
    print("health", health.status, health.read()[:120])
    try:
        code, elapsed, body = post(
            "http://127.0.0.1:3020/api/lab/unified-lora/chat",
            {"message": "Say hello in one short sentence.", "max_tokens": 48},
        )
        print("chat", code, f"{elapsed:.1f}s", body[:400])
    except urllib.error.HTTPError as e:
        print("chat HTTP", e.code, e.read()[:400])
    except Exception as e:
        print("chat error", e)
