#!/bin/bash
# Add api.s2artslab.com routes for Deep Key lab chat (gateway :3020).
set -euo pipefail
CONF="${1:-/etc/nginx/sites-enabled/s2artslab.com}"
if grep -q 'location /lab/' "$CONF"; then
  echo "Already configured: location /lab/"
  exit 0
fi
MARKER='location /api/public/ {'
if ! grep -q "$MARKER" "$CONF"; then
  echo "Marker not found in $CONF" >&2
  exit 1
fi
python3 - "$CONF" <<'PY'
import sys
path = sys.argv[1]
text = open(path, encoding='utf-8').read()
block = """
    location /lab/ {
        auth_basic off;
        proxy_pass http://127.0.0.1:3020/lab/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }

    location /api/lab/ {
        auth_basic off;
        proxy_pass http://127.0.0.1:3020/api/lab/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Accept, Origin" always;
    }

"""
needle = "    location /api/public/ {"
if needle not in text:
    raise SystemExit("needle missing")
open(path, 'w', encoding='utf-8').write(text.replace(needle, block + needle, 1))
print("patched", path)
PY
nginx -t
systemctl reload nginx
echo "nginx reloaded"
