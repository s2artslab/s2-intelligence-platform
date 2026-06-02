#!/usr/bin/env bash
# Pull coding-oriented Ollama models on r730 (Tesla P40 24GB).
# Run on r730: bash scripts/r730-pull-cursor-coder-models.sh

set -euo pipefail

echo "Pulling coder models for Cursor local chat..."
ollama pull qwen2.5-coder:7b
echo ""
echo "Installed models:"
ollama list | head -20
echo ""
echo "From workstation: .\scripts\start-r730-inference-tunnel.ps1"
echo "Cursor base URL: http://127.0.0.1:11434/v1"
echo "Suggested model: qwen2.5-coder:7b (or s2-ake:latest for S2 voice)"
