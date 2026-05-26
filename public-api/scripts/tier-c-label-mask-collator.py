#!/usr/bin/env python3
"""
Tier C — mask loss to Ake: completion tokens only.

Copy to r730: /opt/s2-ecosystem/egregore-training/scripts/tier_c_label_mask_collator.py

Usage with HuggingFace Trainer:
  collator = TierCLabelMaskCollator(tokenizer, response_prefix="Ake:")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import torch


@dataclass
class TierCLabelMaskCollator:
    tokenizer: Any
    response_prefix: str = "Ake:"
    max_length: int = 2048
    pad_to_multiple_of: Optional[int] = None

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        texts = []
        for f in features:
            if "text" in f:
                texts.append(f["text"])
            elif "input" in f:
                texts.append(f["input"])
            else:
                system = f.get("system", "")
                user = f.get("user", f.get("question", ""))
                assistant = f.get("assistant", f.get("ake_response", ""))
                texts.append(self._format_turn(system, user, assistant))

        batch = self.tokenizer(
            texts,
            truncation=True,
            max_length=self.max_length,
            padding=True,
            return_tensors="pt",
        )
        labels = batch["input_ids"].clone()
        for i, text in enumerate(texts):
            prefix = text.split(self.response_prefix, 1)[0] + self.response_prefix
            prefix_ids = self.tokenizer(
                prefix,
                truncation=True,
                max_length=self.max_length,
                add_special_tokens=False,
            )["input_ids"]
            mask_len = min(len(prefix_ids), labels.shape[1])
            labels[i, :mask_len] = -100

        pad_id = self.tokenizer.pad_token_id
        if pad_id is not None:
            labels[labels == pad_id] = -100

        batch["labels"] = labels
        return batch

    def _format_turn(self, system: str, user: str, assistant: str) -> str:
        system = (system or "").strip()
        user = (user or "").strip()
        assistant = (assistant or "").strip()
        if not assistant.startswith(self.response_prefix):
            assistant = f"{self.response_prefix} {assistant}"
        block = f"{system}\n\n---\n\nUser question:\n{user}\n\n{assistant}"
        return block.strip()


if __name__ == "__main__":
    print("TierCLabelMaskCollator — import from training script on r730.")
