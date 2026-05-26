#!/usr/bin/env python3
import re
from pathlib import Path

p = Path("/opt/s2-ecosystem/egregore-training/unified_egregore_service/app.py")
t = p.read_text()
old = "        response = response.strip()\n        return jsonify({"
new = """        response = response.strip()
        # Drop leading list-style debris (foundation template artifact)
        response = re.sub(r"^(?:\\d+:\\s*)+", "", response).strip()
        return jsonify({"""
if old in t and "re.sub" not in t.split(old)[0][-200:]:
    if "import re" not in t:
        t = t.replace("import os\n", "import os\nimport re\n", 1)
    t = t.replace(old, new, 1)
    p.write_text(t)
    print("prefix strip ok")
else:
    print("skip prefix")
