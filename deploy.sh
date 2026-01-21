#!/bin/bash
# S2 Intelligence Platform - Basic Deployment Script
# Community Edition (Open Source)

echo "================================================================"
echo "S2 Intelligence Platform - Deployment"
echo "Community Edition (Open Source)"
echo "================================================================"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then 
    echo "Error: Python 3.8+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION detected"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✓ Virtual environment created"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -q flask requests redis
echo "✓ Dependencies installed"
echo ""

# Configuration
echo "================================================================"
echo "DEPLOYMENT TYPE"
echo "================================================================"
echo ""
echo "This is the Community Edition (Open Source) with basic features."
echo ""
echo "Included:"
echo "  ✓ Basic intelligence router"
echo "  ✓ Content-based routing"
echo "  ✓ Benchmark scripts"
echo "  ✓ Training framework"
echo ""
echo "NOT Included (Available in S2 Premium):"
echo "  • Consciousness tracking algorithms"
echo "  • Trained S2-domain models"
echo "  • Advanced semantic routing"
echo "  • BIPRA storage integration"
echo "  • Multi-agent orchestration"
echo "  • 78% cache optimization"
echo ""
echo "================================================================"
echo ""

# Ask about backend setup
echo "Do you have a local LLM backend? (y/n)"
read -r HAS_BACKEND

if [ "$HAS_BACKEND" = "y" ]; then
    echo ""
    echo "Configure your backend in intelligence_router.py:"
    echo "  BACKENDS = {"
    echo "    'pythia': {'url': 'http://localhost:8090/api/generate'}"
    echo "  }"
    echo ""
else
    echo ""
    echo "You'll need to set up a backend LLM:"
    echo "  - Ollama (https://ollama.ai)"
    echo "  - vLLM (https://github.com/vllm-project/vllm)"
    echo "  - Text Generation Inference"
    echo "  - Or use cloud APIs (Groq, OpenAI, etc.)"
    echo ""
fi

echo "================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================"
echo ""
echo "Start the router:"
echo "  python intelligence_router.py"
echo ""
echo "Run benchmarks:"
echo "  python benchmarks/hybrid_orchestration_test.py"
echo ""
echo "View dashboard:"
echo "  Open S2_BENCHMARK_DASHBOARD.html in browser"
echo ""
echo "================================================================"
echo "UPGRADE TO S2 PREMIUM"
echo "================================================================"
echo ""
echo "For the full S2 Intelligence experience with:"
echo "  • 100% consciousness tracking"
echo "  • 4x domain advantage"
echo "  • Trained egregore models"
echo "  • Advanced orchestration"
echo ""
echo "Contact: beta@s2intelligence.com"
echo "GitHub: https://github.com/s2artslab/s2-intelligence-platform"
echo ""
echo "================================================================"
