#!/usr/bin/env python3
"""
Patch unified_egregore_service on r730 for QLoRA-style inference (4-bit base + LoRA).
Idempotent — safe to re-run. Does not restart systemd (use setup-unified-4bit-r730.sh).

  python3 apply-unified-4bit-inference-patch-r730.py
  python3 apply-unified-4bit-inference-patch-r730.py --eg-dir /opt/s2-ecosystem/egregore-training
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CONFIG_MARKER = "LOAD_IN_4BIT = os.environ.get"
APP_MARKER = "def _base_model_load_kwargs("
HEALTH_MARKER = '"load_in_4bit"'


def patch_config(config_path: Path) -> bool:
    text = config_path.read_text(encoding="utf-8")
    if CONFIG_MARKER in text:
        print(f"  config.py: already patched ({config_path})")
        return False
    needle = 'DEVICE = os.environ.get("EGREGORE_DEVICE", "auto")'
    insert = '''DEVICE = os.environ.get("EGREGORE_DEVICE", "auto")
# QLoRA-style inference: 4-bit NF4 base (matches train_egregore_on_foundation_7b.py --qlora)
LOAD_IN_4BIT = os.environ.get("EGREGORE_LOAD_IN_4BIT", "0") == "1"'''
    if needle not in text:
        print(f"  config.py: anchor not found — manual patch required ({config_path})", file=sys.stderr)
        return False
    config_path.write_text(text.replace(needle, insert, 1), encoding="utf-8")
    print(f"  config.py: patched ({config_path})")
    return True


def patch_app(app_path: Path) -> bool:
    text = app_path.read_text(encoding="utf-8")
    changed = False

    if "from config import" in text and "LOAD_IN_4BIT" not in text:
        text = text.replace(
            "    DEVICE, USE_CPU_OFFLOAD, REPETITION_PENALTY, NO_REPEAT_NGRAM_SIZE,",
            "    DEVICE, LOAD_IN_4BIT, USE_CPU_OFFLOAD, REPETITION_PENALTY, NO_REPEAT_NGRAM_SIZE,",
            1,
        )
        changed = True

    if APP_MARKER not in text:
        helper = '''

def _base_model_load_kwargs(base_model: str, device: str, device_map):
    """Build from_pretrained kwargs; 4-bit path mirrors Tier C QLoRA training."""
    if LOAD_IN_4BIT:
        if device != "cuda":
            raise RuntimeError("EGREGORE_LOAD_IN_4BIT=1 requires EGREGORE_DEVICE=cuda and P40 venv")
        from transformers import BitsAndBytesConfig

        return {
            "trust_remote_code": True,
            "quantization_config": BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            ),
            "device_map": "auto",
            "low_cpu_mem_usage": True,
        }
    use_fp16 = device == "cuda"
    kwargs = {
        "torch_dtype": torch.float16 if use_fp16 else torch.float32,
        "trust_remote_code": True,
    }
    if device_map:
        kwargs["device_map"] = device_map
    return kwargs

'''
        anchor = "\ndef get_model(egregore):"
        if anchor not in text:
            print(f"  app.py: get_model anchor not found ({app_path})", file=sys.stderr)
            return False
        text = text.replace(anchor, helper + anchor, 1)
        changed = True

    old_block = """        use_fp16 = device == "cuda"
        print(f"Loading adapter for {egregore} (base={base_model}, adapters={len(adapter_paths)}, device={device})...")

        base = AutoModelForCausalLM.from_pretrained(
            base_model,
            torch_dtype=torch.float16 if use_fp16 else torch.float32,
            device_map=device_map if device_map else None,
            trust_remote_code=True,
        )
        if device == "cpu":
            base = base.to("cpu")"""

    new_block = """        mode = "4bit-cuda" if LOAD_IN_4BIT else device
        print(
            f"Loading adapter for {egregore} (base={base_model}, adapters={len(adapter_paths)}, mode={mode})..."
        )

        base = AutoModelForCausalLM.from_pretrained(
            base_model,
            **_base_model_load_kwargs(base_model, device, device_map),
        )
        if device == "cpu" and not LOAD_IN_4BIT:
            base = base.to("cpu")"""

    if old_block in text:
        text = text.replace(old_block, new_block, 1)
        changed = True
    elif new_block.split("\n")[2] in text:
        print(f"  app.py: load block already patched ({app_path})")
    else:
        print(f"  app.py: load block anchor not found — manual patch required ({app_path})", file=sys.stderr)
        return False

    if HEALTH_MARKER not in text:
        text = re.sub(
            r'(\s+"status":\s*"healthy",)',
            r'\1\n        "device": DEVICE,\n        "load_in_4bit": LOAD_IN_4BIT,',
            text,
            count=1,
        )
        if HEALTH_MARKER not in text:
            # fallback: append fields before closing brace of health dict
            text = text.replace(
                '"status": "healthy"',
                '"status": "healthy", "device": DEVICE, "load_in_4bit": LOAD_IN_4BIT',
                1,
            )
        changed = True

    if changed:
        app_path.write_text(text, encoding="utf-8")
        print(f"  app.py: patched ({app_path})")
    else:
        print(f"  app.py: already patched ({app_path})")
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--eg-dir",
        default="/opt/s2-ecosystem/egregore-training",
        help="egregore-training root on r730",
    )
    args = ap.parse_args()
    svc = Path(args.eg_dir) / "unified_egregore_service"
    config_path = svc / "config.py"
    app_path = svc / "app.py"
    if not config_path.is_file() or not app_path.is_file():
        print(f"Missing unified service under {svc}", file=sys.stderr)
        return 1
    print(f"Patching unified egregore 4-bit inference under {svc} ...")
    c = patch_config(config_path)
    a = patch_app(app_path)
    if c or a:
        print("Done. Restart with: bash scripts/setup-unified-4bit-r730.sh")
    else:
        print("No changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
