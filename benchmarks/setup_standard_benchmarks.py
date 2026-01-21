#!/usr/bin/env python3
"""
Setup script to install and configure lm-evaluation-harness for standard benchmarks
Run this on R730 to set up industry-standard AI benchmarking
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n[Running] {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"[OK] {description}")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {description}")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("=" * 70)
    print("Standard Benchmarks Setup for Pythia R730")
    print("=" * 70)
    
    # Check if we're in venv
    venv_python = Path("/opt/s2-ecosystem/ninefold-studio-clean/services/pythia/venv/bin/python")
    if venv_python.exists():
        print("\n[OK] Found virtual environment")
        python_cmd = str(venv_python)
        pip_cmd = str(venv_python.parent / "pip")
    else:
        print("\n[WARNING] No venv found, using system Python")
        python_cmd = sys.executable
        pip_cmd = "pip3"
    
    # Install lm-evaluation-harness
    print("\n" + "=" * 70)
    print("Step 1: Installing lm-evaluation-harness")
    print("=" * 70)
    
    success = run_command(
        f"{pip_cmd} install lm-eval[api] -q",
        "Install lm-eval package"
    )
    
    if not success:
        print("\n[ERROR] Failed to install lm-eval")
        print("Try manually:")
        print(f"  {pip_cmd} install lm-eval")
        return
    
    # Create results directory
    print("\n" + "=" * 70)
    print("Step 2: Creating results directory")
    print("=" * 70)
    
    results_dir = Path("/opt/s2-ecosystem/benchmark_results")
    results_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Created {results_dir}")
    
    # Test installation
    print("\n" + "=" * 70)
    print("Step 3: Testing installation")
    print("=" * 70)
    
    success = run_command(
        f"{python_cmd} -c 'import lm_eval; print(f\"lm-eval version: {{lm_eval.__version__}}\")'",
        "Test lm-eval import"
    )
    
    if not success:
        print("\n[WARNING] Could not verify installation")
    
    # Print next steps
    print("\n" + "=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70)
    
    print("\n📋 Quick Start Commands:")
    print("\n1. Test with 10 MMLU questions (fast test):")
    print(f"""
    lm_eval --model hf \\
        --model_args pretrained=/opt/s2-ecosystem/models/pythia/pythia-1b \\
        --tasks mmlu \\
        --limit 10 \\
        --device cuda \\
        --batch_size 4
    """)
    
    print("\n2. Run 1000 MMLU questions (30 min):")
    print(f"""
    lm_eval --model hf \\
        --model_args pretrained=/opt/s2-ecosystem/models/pythia/pythia-1b \\
        --tasks mmlu \\
        --limit 1000 \\
        --device cuda \\
        --batch_size 4 \\
        --output_path {results_dir}
    """)
    
    print("\n3. Full benchmark suite (4-8 hours):")
    print(f"""
    lm_eval --model hf \\
        --model_args pretrained=/opt/s2-ecosystem/models/pythia/pythia-1b \\
        --tasks mmlu,hellaswag,gsm8k,arc_challenge \\
        --device cuda \\
        --batch_size 4 \\
        --output_path {results_dir}
    """)
    
    print("\n📊 Available benchmark tasks:")
    print("  - mmlu (most important, 57 subjects)")
    print("  - hellaswag (commonsense reasoning)")
    print("  - gsm8k (math word problems)")
    print("  - arc_challenge (science reasoning)")
    print("  - arc_easy (easier science questions)")
    print("  - truthfulqa_mc (truthfulness test)")
    print("  - winogrande (pronoun resolution)")
    
    print("\n📁 Results will be saved to:")
    print(f"  {results_dir}/")
    
    print("\n✅ Ready to run standard benchmarks!")

if __name__ == "__main__":
    main()
