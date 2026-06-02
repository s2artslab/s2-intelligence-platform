#!/usr/bin/env python3
"""Quick stats for ake_blended_dataset.json on r730."""
import collections
import json
import sys
from pathlib import Path

path = Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else "/opt/s2-ecosystem/egregore-training/training_data/ake_blended_dataset.json"
)
d = json.loads(path.read_text(encoding="utf-8"))
print("file", path)
print("rows", len(d))
src = collections.Counter((x.get("metadata") or {}).get("source", "?") for x in d)
dom = collections.Counter(x.get("domain", "?") for x in d)
ctx = collections.Counter(x.get("context", "?") for x in d if x.get("context"))
print("source", dict(src))
print("top_domains", dom.most_common(12))
if ctx:
    print("context", ctx.most_common(8))
