#!/usr/bin/env python3
from pathlib import Path

p = Path("/opt/s2-ecosystem/egregore-training/train_egregore_on_foundation_7b.py")
t = p.read_text(encoding="utf-8")
needle = '        eval_strategy="no",\n    )'
insert = (
    '        eval_strategy="no",\n'
    '        remove_unused_columns=False if os.environ.get("TIER_C_LABEL_MASK") == "1" else True,\n'
    "    )"
)
if "remove_unused_columns=False if os.environ" not in t and needle in t:
    t = t.replace(needle, insert, 1)
    p.write_text(t, encoding="utf-8")
    print("patched remove_unused_columns")
else:
    print("skip or already patched")
