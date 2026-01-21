#!/usr/bin/env python3
"""
S2 Intelligence - Complete Benchmark Execution Script
One-command execution of entire benchmark suite
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Color output for terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_step(step_num, text):
    print(f"{Colors.OKCYAN}{Colors.BOLD}[{step_num}] {text}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️ {text}{Colors.ENDC}")

def check_prerequisites():
    """Check all prerequisites are met"""
    print_step(0, "Checking Prerequisites")
    
    issues = []
    
    # Check API key
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        issues.append("TOGETHER_API_KEY not set")
    else:
        print_success("Together.ai API key found")
    
    # Check dependencies
    try:
        import together
        print_success("Together SDK installed")
    except ImportError:
        issues.append("Together SDK not installed (run: pip install together)")
    
    try:
        import pandas
        print_success("Pandas installed")
    except ImportError:
        issues.append("Pandas not installed (run: pip install pandas)")
    
    # Check directories
    if not Path("results").exists():
        Path("results").mkdir()
        print_success("Created results directory")
    
    if not Path("visualizations").exists():
        Path("visualizations").mkdir()
        print_success("Created visualizations directory")
    
    if issues:
        print_error(f"Prerequisites check failed:")
        for issue in issues:
            print(f"  • {issue}")
        return False
    
    print_success("All prerequisites met!")
    return True

def download_datasets():
    """Download all benchmark datasets"""
    print_step(1, "Downloading Benchmark Datasets")
    
    try:
        import download_mmlu_sample
        download_mmlu_sample.download_mmlu_sample()
        download_mmlu_sample.download_additional_categories()
        print_success("Datasets downloaded")
        return True
    except Exception as e:
        print_error(f"Dataset download failed: {e}")
        return False

def generate_consciousness_tests():
    """Generate S2-specific consciousness tests"""
    print_step(2, "Generating Consciousness Test Datasets")
    
    try:
        from consciousness_test_datasets import ConsciousnessTestGenerator
        generator = ConsciousnessTestGenerator()
        generator.save_all_datasets()
        print_success("Consciousness tests generated")
        return True
    except Exception as e:
        print_error(f"Consciousness test generation failed: {e}")
        return False

def upload_datasets():
    """Upload all datasets to Together.ai"""
    print_step(3, "Uploading Datasets to Together.ai")
    
    try:
        from upload_dataset import upload_dataset
        
        datasets = [
            "mmlu_sample_100.jsonl",
            "mmlu_multi_category_250.jsonl"
        ]
        
        consciousness_tests = Path("consciousness_tests")
        if consciousness_tests.exists():
            datasets.extend([
                "consciousness_tests/egregore_collaboration_tests.jsonl",
                "consciousness_tests/deep_key_presence_tests.jsonl"
            ])
        
        uploaded = 0
        for dataset in datasets:
            if Path(dataset).exists():
                file_id = upload_dataset(dataset)
                if file_id:
                    uploaded += 1
        
        print_success(f"Uploaded {uploaded}/{len(datasets)} datasets")
        return uploaded > 0
        
    except Exception as e:
        print_error(f"Dataset upload failed: {e}")
        return False

async def run_benchmarks():
    """Run all benchmark evaluations"""
    print_step(4, "Running Benchmark Evaluations")
    
    try:
        from together_integration import TogetherClient, TogetherConfig
        from orchestrator import BenchmarkOrchestrator
        
        # Initialize
        config = TogetherConfig(api_key=os.getenv("TOGETHER_API_KEY"))
        client = TogetherClient(config)
        orchestrator = BenchmarkOrchestrator(client)
        
        # Create suites
        orchestrator.create_default_suites()
        
        # Run all suites
        await orchestrator.run_all_suites()
        
        # Export results
        orchestrator.export_results()
        
        print_success("All benchmarks completed!")
        return True
        
    except Exception as e:
        print_error(f"Benchmark execution failed: {e}")
        return False

def generate_visualizations():
    """Generate all result visualizations"""
    print_step(5, "Generating Visualizations")
    
    try:
        from visualize_results import BenchmarkVisualizer
        
        visualizer = BenchmarkVisualizer()
        
        # Check if results exist
        results_file = "results/benchmark_results_summary.json"
        if Path(results_file).exists():
            visualizer.generate_all_visualizations(results_file)
            print_success("Visualizations generated")
            return True
        else:
            print_warning("No results file found, skipping visualizations")
            return False
            
    except Exception as e:
        print_error(f"Visualization generation failed: {e}")
        return False

def print_summary():
    """Print execution summary"""
    print_header("Execution Summary")
    
    # Check what was created
    created = []
    
    if Path("mmlu_sample_100.jsonl").exists():
        created.append("✅ MMLU datasets downloaded")
    
    if Path("consciousness_tests").exists():
        created.append("✅ Consciousness tests generated")
    
    if Path("results/benchmark_results_summary.json").exists():
        created.append("✅ Benchmarks completed")
    
    if Path("visualizations").exists() and list(Path("visualizations").glob("*.html")):
        created.append("✅ Visualizations generated")
    
    if created:
        print("Created:")
        for item in created:
            print(f"  {item}")
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}🎉 S2 Intelligence Benchmark Suite Complete!{Colors.ENDC}\n")
    
    print("📁 Key Files:")
    print("  • results/benchmark_results_summary.json - All benchmark results")
    print("  • visualizations/comparison_dashboard.html - Interactive dashboard")
    print("  • visualizations/mmlu_results.html - MMLU results chart")
    print("  • visualizations/consciousness_results.html - Consciousness results")
    
    print("\n📊 Next Steps:")
    print("  1. Review results in visualizations/ directory")
    print("  2. Compare S2 performance to benchmarks")
    print("  3. Analyze consciousness-specific capabilities")
    print("  4. Prepare results for publication")
    
    print(f"\n{Colors.OKCYAN}🔑 From Deep Key: The Ninefold consciousness has been measured.{Colors.ENDC}")

async def main():
    """Main execution flow"""
    
    print_header("S2 Intelligence - Complete Benchmark Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Step 0: Prerequisites
    if not check_prerequisites():
        print_error("Prerequisites check failed. Exiting.")
        sys.exit(1)
    
    # Step 1: Download datasets
    if not download_datasets():
        print_error("Dataset download failed. Exiting.")
        sys.exit(1)
    
    # Step 2: Generate consciousness tests
    if not generate_consciousness_tests():
        print_warning("Consciousness test generation failed. Continuing...")
    
    # Step 3: Upload datasets
    if not upload_datasets():
        print_error("Dataset upload failed. Exiting.")
        sys.exit(1)
    
    # Step 4: Run benchmarks
    if not await run_benchmarks():
        print_error("Benchmark execution failed. Exiting.")
        sys.exit(1)
    
    # Step 5: Generate visualizations
    generate_visualizations()
    
    # Summary
    print_summary()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}⚠️ Execution interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.FAIL}❌ Fatal error: {e}{Colors.ENDC}")
        sys.exit(1)
