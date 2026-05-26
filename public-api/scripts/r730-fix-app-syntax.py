#!/usr/bin/env python3
from pathlib import Path

p = Path("/opt/s2-ecosystem/egregore-training/unified_egregore_service/app.py")
t = p.read_text()
needle = "def generate_tokens(\n\ndef _resolve_generation_options"
if needle in t:
    t = t.replace(needle, "def _resolve_generation_options", 1)
    t = t.replace(
        "        return model.generate(**gen_kw)\nmodel, inputs, max_new_tokens=200",
        "        return model.generate(**gen_kw)\n\n\ndef generate_tokens(model, inputs, max_new_tokens=200",
        1,
    )
    p.write_text(t)
    print("fixed syntax")
else:
    print("already ok or unknown layout")
