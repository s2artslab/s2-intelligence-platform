#!/usr/bin/env python3
"""
QLoRA fine-tune Ake LoRA on Llama 3.2 (Ollama-aligned base).

No Mistral / s2_foundation stack — single adapter for merge into Ollama s2-ake-lora.

Install on r730:
  cp public-api/scripts/train_egregore_on_llama32.py /opt/s2-ecosystem/egregore-training/
  cp public-api/scripts/tier-c-label-mask-collator.py /opt/s2-ecosystem/egregore-training/scripts/tier_c_label_mask_collator.py

Usage:
  export TIER_C_BLENDED=/path/to/ake_tier_cde_blended_v4.json
  export TIER_C_LABEL_MASK=1
  export OUTPUT_DIR=/mnt/bipra/egregore-training/trained_models/ake-llama32
  venv/bin/python train_egregore_on_llama32.py ake --qlora --epochs 2
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_BASE = os.environ.get("BASE_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
DEFAULT_OUTPUT = os.environ.get(
    "OUTPUT_DIR", "/mnt/bipra/egregore-training/trained_models/ake-llama32"
)
DEFAULT_BLEND = os.environ.get(
    "TIER_C_BLENDED",
    "/opt/s2-ecosystem/egregore-training/training_data/ake_tier_cde_blended_v4.json",
)

LLAMA_LORA_TARGETS = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]


def _load_texts(path: Path) -> list[str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    texts: list[str] = []
    for item in raw:
        if isinstance(item, str):
            texts.append(item.strip())
            continue
        if "text" in item:
            texts.append(str(item["text"]).strip())
            continue
        question = (item.get("question") or "").strip()
        response = (item.get("ake_response") or item.get("assistant") or "").strip()
        if not question or not response:
            system = (item.get("system") or "").strip()
            user = (item.get("user") or item.get("question") or "").strip()
            assistant = (item.get("assistant") or item.get("ake_response") or "").strip()
            if system or user:
                question = f"{system}\n\n---\n\nUser question:\n{user}".strip()
                response = assistant.replace("Ake:", "", 1).strip() if assistant else ""
        if not question or not response:
            continue
        if not response.startswith("Ake:"):
            response = f"Ake: {response}"
        texts.append(f"{question}\n\n{response}".strip())
    return texts


def main() -> int:
    ap = argparse.ArgumentParser(description="QLoRA Ake on Llama 3.2")
    ap.add_argument("egregore", nargs="?", default="ake")
    ap.add_argument("--qlora", action="store_true", help="4-bit QLoRA (required on P40)")
    ap.add_argument("--epochs", type=float, default=float(os.environ.get("TRAIN_EPOCHS", "2")))
    ap.add_argument("--base-model", default=DEFAULT_BASE)
    ap.add_argument("--dataset", default=DEFAULT_BLEND)
    ap.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    ap.add_argument("--batch-size", type=int, default=int(os.environ.get("TRAIN_BATCH_SIZE", "1")))
    ap.add_argument("--grad-accum", type=int, default=int(os.environ.get("TRAIN_GRAD_ACCUM", "4")))
    ap.add_argument("--lr", type=float, default=float(os.environ.get("TRAIN_LR", "2e-4")))
    ap.add_argument("--max-length", type=int, default=int(os.environ.get("TRAIN_MAX_LENGTH", "2048")))
    args = ap.parse_args()

    if not args.qlora:
        logger.error("P40 requires --qlora for Llama 3.2 training")
        return 1

    dataset_path = Path(args.dataset)
    if not dataset_path.is_file():
        logger.error("Dataset not found: %s", dataset_path)
        return 1

    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
            Trainer,
        )
    except ImportError as exc:
        logger.error("Missing deps (torch, transformers, peft, datasets, bitsandbytes): %s", exc)
        return 1

    scripts_dir = Path(__file__).resolve().parent / "scripts"
    if not scripts_dir.is_dir():
        scripts_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(scripts_dir.parent))
    sys.path.insert(0, str(scripts_dir))

    use_label_mask = os.environ.get("TIER_C_LABEL_MASK") == "1"
    collator = None
    if use_label_mask:
        from tier_c_label_mask_collator import TierCLabelMaskCollator

        collator = TierCLabelMaskCollator

    logger.info("=" * 70)
    logger.info("QLoRA AKE ON LLAMA 3.2: %s", args.egregore.upper())
    logger.info("=" * 70)
    logger.info("Base model: %s", args.base_model)
    logger.info("Dataset: %s", dataset_path)
    logger.info("Output: %s", args.output_dir)
    logger.info("Label mask on Ake: tokens only: %s", use_label_mask)
    logger.info("=" * 70)

    texts = _load_texts(dataset_path)
    if not texts:
        logger.error("No training texts prepared from %s", dataset_path)
        return 1
    logger.info("Prepared %d training texts", len(texts))

    if use_label_mask:
        rows = [{"text": t} for t in texts]
    else:
        rows = texts

    train_ds = Dataset.from_dict({"text": texts}) if not use_label_mask else Dataset.from_list(rows)

    logger.info("Loading tokenizer: %s...", args.base_model)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    logger.info("Loading base model (4-bit): %s...", args.base_model)
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=int(os.environ.get("LORA_R", "16")),
        lora_alpha=int(os.environ.get("LORA_ALPHA", "32")),
        target_modules=LLAMA_LORA_TARGETS,
        lora_dropout=float(os.environ.get("LORA_DROPOUT", "0.05")),
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    def tokenize_batch(examples):
        out = tokenizer(
            examples["text"],
            truncation=True,
            max_length=args.max_length,
            padding=False,
        )
        out["labels"] = [ids[:] for ids in out["input_ids"]]
        return out

    if use_label_mask:
        tokenized = train_ds
    else:
        tokenized = train_ds.map(tokenize_batch, batched=True, remove_columns=["text"])

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(out_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        logging_steps=50,
        save_steps=500,
        save_total_limit=2,
        fp16=True,
        optim="paged_adamw_8bit",
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="none",
        eval_strategy="no",
        remove_unused_columns=False if use_label_mask else True,
    )

    data_collator = None
    if use_label_mask and collator is not None:
        data_collator = collator(tokenizer=tokenizer, max_length=args.max_length)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    logger.info("Starting Llama 3.2 QLoRA training...")
    trainer.train()
    trainer.save_model(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))

    logger.info("=" * 70)
    logger.info("Training completed!")
    logger.info("Adapter saved to %s", out_dir)
    logger.info("Next: bash public-api/scripts/deploy-ake-lora-ollama-r730.sh")
    logger.info("=" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
