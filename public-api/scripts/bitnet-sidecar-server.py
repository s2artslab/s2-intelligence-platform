#!/usr/bin/env python3
"""
HTTP sidecar for BitNet b1.58 inference (port 8120).
Wraps microsoft/BitNet run_inference.py when installed; stub mode for dev/CI.

  python3 scripts/bitnet-sidecar-server.py
  BITNET_STUB=1 python3 scripts/bitnet-sidecar-server.py

Endpoints:
  GET  /health
  POST /generate  { prompt, max_tokens, temperature, task_class }
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

PORT = int(os.environ.get("BITNET_SIDECAR_PORT", "8120"))
HOST = os.environ.get("BITNET_SIDECAR_HOST", "127.0.0.1")
BITNET_ROOT = Path(os.environ.get("BITNET_ROOT", "/opt/bitnet.cpp"))
MODEL_PATH = os.environ.get(
    "BITNET_MODEL_PATH",
    str(BITNET_ROOT / "models" / "BitNet-b1.58-2B-4T" / "ggml-model-i2_s.gguf"),
)
LORA_ADAPTER_PATH = os.environ.get("BITNET_LORA_ADAPTER_PATH", "").strip()
QVAC_CLI = os.environ.get(
    "BITNET_QVAC_CLI",
    "/opt/qvac-fabric-llm.cpp/build/bin/llama-cli",
).strip()
QVAC_MODEL_PATH = os.environ.get("BITNET_QVAC_MODEL_PATH", "").strip()
EGREGORE_REGISTRY_PATH = os.environ.get("BITNET_EGREGORE_REGISTRY", "").strip()
RUN_INFERENCE = BITNET_ROOT / "run_inference.py"
STUB_MODE = os.environ.get("BITNET_STUB", "0") == "1" or os.environ.get("BITNET_STUB_MODE", "0") == "1"
DEFAULT_MODEL = os.environ.get("BITNET_MODEL", "bitnet-b1.58-2B-4T")


def _load_egregore_registry() -> dict[str, str]:
    if not EGREGORE_REGISTRY_PATH or not Path(EGREGORE_REGISTRY_PATH).is_file():
        return {}
    try:
        data = json.loads(Path(EGREGORE_REGISTRY_PATH).read_text(encoding="utf-8"))
        return {str(k): str(v) for k, v in data.items() if v}
    except (json.JSONDecodeError, OSError):
        return {}


def _resolve_lora_adapter(egregore_id: str | None) -> str:
    reg = _load_egregore_registry()
    if egregore_id:
        eg = egregore_id.strip().lower()
        if eg in reg and Path(reg[eg]).is_file():
            return reg[eg]
    if LORA_ADAPTER_PATH and Path(LORA_ADAPTER_PATH).is_file():
        return LORA_ADAPTER_PATH
    return ""


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _health() -> dict[str, Any]:
    model_exists = Path(MODEL_PATH).is_file()
    inference_ready = RUN_INFERENCE.is_file() and model_exists
    reg = _load_egregore_registry()
    return {
        "ok": STUB_MODE or inference_ready,
        "service": "bitnet-sidecar",
        "port": PORT,
        "model": DEFAULT_MODEL,
        "quantization": "w1.58a8",
        "quantization_bits": 1.58,
        "backend": "bitnet.cpp" if inference_ready else ("stub" if STUB_MODE else "missing"),
        "stub_mode": STUB_MODE,
        "model_path": MODEL_PATH,
        "lora_adapter_path": LORA_ADAPTER_PATH or None,
        "lora_adapter_present": bool(LORA_ADAPTER_PATH and Path(LORA_ADAPTER_PATH).is_file()),
        "egregore_registry_path": EGREGORE_REGISTRY_PATH or None,
        "egregore_adapters": list(reg.keys()),
        "egregore_adapter_count": len(reg),
        "model_present": model_exists,
        "run_inference_present": RUN_INFERENCE.is_file(),
        "bitnet_root": str(BITNET_ROOT),
        "qvac_cli_present": bool(QVAC_CLI and Path(QVAC_CLI).is_file()),
        "qvac_model_path": QVAC_MODEL_PATH or None,
    }


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _stub_generate(prompt: str, max_tokens: int, task_class: str) -> dict[str, Any]:
    preview = prompt.strip().split("\n")[-1][:120]
    response = (
        f"[BitNet stub · {task_class or 'compact'}] "
        f"Processed: {preview or 'empty prompt'}. "
        "Install bitnet.cpp on r730 for live 1.58-bit inference."
    )
    if max_tokens < len(response.split()):
        response = " ".join(response.split()[: max(8, max_tokens)])
    return {
        "ok": True,
        "response": response,
        "content": response,
        "model": DEFAULT_MODEL,
        "quantization_bits": 1.58,
        "prompt_tokens": _estimate_tokens(prompt),
        "completion_tokens": _estimate_tokens(response),
        "memory_mb": 0.4,
        "stub_mode": True,
        "task_class": task_class,
    }


def _qvac_generate(
    prompt: str,
    max_tokens: int,
    lora_path: str,
) -> dict[str, Any]:
    if not QVAC_MODEL_PATH or not Path(QVAC_MODEL_PATH).is_file():
        raise RuntimeError(f"BITNET_QVAC_MODEL_PATH missing: {QVAC_MODEL_PATH}")
    if not Path(QVAC_CLI).is_file():
        raise RuntimeError(f"BITNET_QVAC_CLI missing: {QVAC_CLI}")
    started = time.time()
    cmd = [
        QVAC_CLI,
        "-m",
        QVAC_MODEL_PATH,
        "--lora",
        lora_path,
        "-p",
        prompt,
        "-n",
        str(max_tokens),
        "--flash-attn",
        "off",
        "--no-display-prompt",
    ]
    ngl = int(os.environ.get("BITNET_QVAC_NGL", "999"))
    if ngl > 0:
        cmd.extend(["-ngl", str(ngl)])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=int(os.environ.get("BITNET_INFERENCE_TIMEOUT", "180")),
    )
    latency_ms = int((time.time() - started) * 1000)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")
    response = proc.stdout.strip()
    return {
        "ok": True,
        "response": response,
        "content": response,
        "model": DEFAULT_MODEL,
        "quantization_bits": 1.58,
        "latency_ms": latency_ms,
        "prompt_tokens": _estimate_tokens(prompt),
        "completion_tokens": _estimate_tokens(response),
        "memory_mb": 0.4,
        "stub_mode": False,
        "backend": "qvac-fabric",
        "lora_adapter_path": lora_path,
    }


def _live_generate(
    prompt: str,
    max_tokens: int,
    temperature: float,
    task_class: str,
    egregore_id: str = "",
) -> dict[str, Any]:
    started = time.time()
    lora_path = _resolve_lora_adapter(egregore_id or None)
    if lora_path and QVAC_MODEL_PATH and Path(QVAC_CLI).is_file():
        out = _qvac_generate(prompt, max_tokens, lora_path)
        out["task_class"] = task_class
        out["egregore_id"] = egregore_id or None
        return out
    cmd = [
        sys.executable,
        str(RUN_INFERENCE),
        "-m",
        MODEL_PATH,
        "-p",
        prompt,
        "-n",
        str(max_tokens),
        "-t",
        str(max(1, min(8, os.cpu_count() or 4))),
    ]
    if temperature <= 0.15:
        cmd.append("-cnv")
    if lora_path:
        cmd.extend(["--lora", lora_path])

    proc = subprocess.run(
        cmd,
        cwd=str(BITNET_ROOT),
        capture_output=True,
        text=True,
        timeout=int(os.environ.get("BITNET_INFERENCE_TIMEOUT", "120")),
    )
    latency_ms = int((time.time() - started) * 1000)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}")

    response = proc.stdout.strip()
    return {
        "ok": True,
        "response": response,
        "content": response,
        "model": DEFAULT_MODEL,
        "quantization_bits": 1.58,
        "latency_ms": latency_ms,
        "prompt_tokens": _estimate_tokens(prompt),
        "completion_tokens": _estimate_tokens(response),
        "memory_mb": 0.4,
        "stub_mode": False,
        "task_class": task_class,
        "egregore_id": egregore_id or None,
        "lora_adapter_path": lora_path or None,
    }


def _generate(body: dict[str, Any]) -> dict[str, Any]:
    prompt = str(body.get("prompt") or "").strip()
    messages = body.get("messages") or []
    if not prompt and messages:
        prompt = "\n".join(
            f"{m.get('role', 'user').title()}: {str(m.get('content', '')).strip()}"
            for m in messages
            if m.get("content")
        )
    if not prompt:
        raise ValueError("Missing prompt")

    max_tokens = int(body.get("max_tokens") or body.get("max_length") or 256)
    temperature = float(body.get("temperature") or 0.2)
    task_class = str(body.get("task_class") or body.get("taskClass") or "compact")
    egregore_id = str(body.get("egregore_id") or body.get("egregore") or "").strip().lower()

    started = time.time()
    if STUB_MODE or not (RUN_INFERENCE.is_file() and Path(MODEL_PATH).is_file()):
        out = _stub_generate(prompt, max_tokens, task_class)
        if egregore_id:
            out["egregore_id"] = egregore_id
    else:
        out = _live_generate(prompt, max_tokens, temperature, task_class, egregore_id)

    if "latency_ms" not in out:
        out["latency_ms"] = int((time.time() - started) * 1000)
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/health":
            _json_response(self, 200, _health())
            return
        _json_response(self, 404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") not in ("/generate", "/v1/completions"):
            _json_response(self, 404, {"ok": False, "error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            body = json.loads(raw) if raw.strip() else {}
            result = _generate(body)
            _json_response(self, 200, result)
        except Exception as e:  # noqa: BLE001
            _json_response(self, 500, {"ok": False, "error": str(e)})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"BitNet sidecar listening on http://{HOST}:{PORT} stub={STUB_MODE}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
