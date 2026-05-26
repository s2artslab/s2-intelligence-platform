#!/usr/bin/env python3
"""Trim degenerate multi-paragraph loops in unified generate response."""
from pathlib import Path

p = Path("/opt/s2-ecosystem/egregore-training/unified_egregore_service/app.py")
t = p.read_text()
old = '        response = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)\n        return jsonify({'
new = '''        response = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
        # Tier A: stop at first blank line (training used single-turn \\n\\n blocks)
        if "\\n\\n" in response:
            response = response.split("\\n\\n")[0]
        response = response.strip()
        return jsonify({'''
if old in t and "split" not in t[t.find(old) : t.find(old) + 200]:
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("trim patched")
else:
    print("skip trim", "already" if "split" in t else "miss")
