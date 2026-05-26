#!/usr/bin/env python3
import pathlib
import subprocess
import sys

path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/etc/nginx/sites-enabled/s2artslab.com")
text = path.read_text(encoding="utf-8")
if "location /lab/" in text:
    print("skip: already has /lab/")
    sys.exit(0)
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
    print("needle missing", file=sys.stderr)
    sys.exit(1)
path.write_text(text.replace(needle, block + needle, 1), encoding="utf-8")
print("patched", path)
subprocess.run(["nginx", "-t"], check=True)
subprocess.run(["systemctl", "reload", "nginx"], check=True)
print("nginx reloaded")
