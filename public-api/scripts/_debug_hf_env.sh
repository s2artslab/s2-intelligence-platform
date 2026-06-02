#!/usr/bin/env bash
for f in \
  /root/ninefold-studio-clean/egregorelab/.env \
  /opt/s2-ecosystem/ninefold-studio-clean/.env \
  /opt/s2-ecosystem/ninefold-studio-clean/egregorelab/.env \
  /opt/s2-ecosystem/s2-ecosystem-minimal/.env \
  /opt/s2-ecosystem/public-api/.env \
  /opt/supabase/.env \
  /opt/s2-marketing/.env; do
  if [[ -f "$f" ]]; then
    echo "== $f =="
    grep -E '^(HUGGINGFACE_API_KEY|HF_TOKEN)=' "$f" | while IFS= read -r line; do
      key="${line%%=*}"
      val="${line#*=}"
      echo "$key value_len=${#val}"
    done
  fi
done
