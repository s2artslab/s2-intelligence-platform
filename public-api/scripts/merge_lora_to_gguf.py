#!/usr/bin/env python3
"""
Merge a PEFT LoRA adapter into a base HF model and export GGUF via llama.cpp.

Run on r730 (GPU recommended). Example:

  python scripts/merge_lora_to_gguf.py \\
    --base-model meta-llama/Llama-3.2-3B-Instruct \\
    --adapter /opt/s2-ecosystem/egregore-training/ake/models/lora \\
    --out-dir /opt/s2-ecosystem/egregore-training/ake/models/gguf \\
    --llama-cpp /opt/llama.cpp \\
    --quantize q4_k_m
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge LoRA and export GGUF for Ollama")
    ap.add_argument("--base-model", required=True, help="HF model id or local path")
    ap.add_argument("--adapter", required=True, help="PEFT adapter directory")
    ap.add_argument("--out-dir", required=True, help="Output directory for GGUF")
    ap.add_argument(
        "--llama-cpp",
        default="/opt/llama.cpp",
        help="Path to llama.cpp repo (convert_hf_to_gguf.py)",
    )
    ap.add_argument(
        "--quantize",
        default="q4_k_m",
        help="llama.cpp quant type (e.g. q4_k_m, q5_k_m, f16)",
    )
    ap.add_argument("--merged-hf-dir", default=None, help="Optional merged HF save dir")
    args = ap.parse_args()

    adapter = Path(args.adapter)
    if not (adapter / "adapter_config.json").exists():
        print(f"ERROR: No adapter at {adapter}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    merged_dir = Path(args.merged_hf_dir or out_dir / "merged-hf")
    merged_dir.mkdir(parents=True, exist_ok=True)

    print("Loading base + LoRA and merging weights...")
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        print(f"ERROR: pip install torch transformers peft accelerate — {e}", file=sys.stderr)
        return 1

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    base = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base, str(adapter))
    merged = model.merge_and_unload()
    merged.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)
    print(f"Merged HF saved: {merged_dir}")

    convert = Path(args.llama_cpp) / "convert_hf_to_gguf.py"
    if not convert.exists():
        print(f"ERROR: llama.cpp convert not found at {convert}", file=sys.stderr)
        print("Clone: git clone https://github.com/ggerganov/llama.cpp /opt/llama.cpp")
        return 1

    gguf_f16 = out_dir / "s2-ake-lora-f16.gguf"
    print("Converting merged HF → GGUF (f16)...")
    subprocess.run(
        [sys.executable, str(convert), str(merged_dir), "--outfile", str(gguf_f16), "--outtype", "f16"],
        check=True,
    )

    final = out_dir / f"s2-ake-lora-{args.quantize}.gguf"
    if args.quantize != "f16":
        quant_bin = Path(args.llama_cpp) / "llama-quantize"
        if not quant_bin.exists():
            quant_bin = Path(args.llama_cpp) / "build" / "bin" / "llama-quantize"
        if not quant_bin.exists():
            print(f"WARN: llama-quantize not found; using f16 GGUF at {gguf_f16}")
            final = gguf_f16
        else:
            print(f"Quantizing → {args.quantize}...")
            subprocess.run([str(quant_bin), str(gguf_f16), str(final), args.quantize], check=True)
    else:
        final = gguf_f16

    manifest = {
        "gguf": str(final),
        "base_model": args.base_model,
        "adapter": str(adapter),
        "quantize": args.quantize,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Done. GGUF: {final}")
    print(f"Next: bash scripts/create-s2-ake-lora-r730.sh --gguf {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
