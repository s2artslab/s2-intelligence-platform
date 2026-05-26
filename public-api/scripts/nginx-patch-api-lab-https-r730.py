#!/usr/bin/env python3
"""Ensure api.s2artslab.com HTTPS block has /lab/, /api/lab/, and /favicon.ico without basic auth."""
import pathlib
import re
import subprocess
import sys

path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/etc/nginx/sites-enabled/s2artslab.com")
text = path.read_text(encoding="utf-8")

lab_block = """
    location = /favicon.ico {
        auth_basic off;
        proxy_pass http://127.0.0.1:3020/favicon.ico;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        access_log off;
    }

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

pattern = re.compile(
    r"(server\s*\{[^}]*listen\s+443[^;]*;[^}]*server_name\s+api\.s2artslab\.com;)"
    r"([\s\S]*?)"
    r"(\n\s*location\s+/api/public/\s*\{)",
    re.MULTILINE,
)

m = pattern.search(text)
if not m:
    print("HTTPS api server block not found", file=sys.stderr)
    sys.exit(1)

segment = m.group(2)
if "location /lab/" in segment and "location = /favicon.ico" in segment:
    print("skip: HTTPS api block already has lab + favicon")
    sys.exit(0)

new_text = text[: m.start(2)] + lab_block + text[m.start(2) :]
path.write_text(new_text, encoding="utf-8")
print("patched HTTPS api block:", path)
subprocess.run(["nginx", "-t"], check=True)
subprocess.run(["systemctl", "reload", "nginx"], check=True)
print("nginx reloaded")
