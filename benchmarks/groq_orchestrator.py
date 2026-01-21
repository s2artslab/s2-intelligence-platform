#!/usr/bin/env python3
"""
Groq Benchmark Orchestrator
Runs complete benchmark suites with Groq API
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from groq_benchmark import GroqBenchmarkRunner

class GroqBenchmarkSuite:
    """Orchestrates multiple Groq benchmarks"""
    
    def __init__(self):
        self.runner = GroqBenchmarkRunner()
        self.results_dir = Path("results")
        
        # Define test suites
        self.suites = {
            "mmlu_pilot": {
                "name": "MMLU Pilot Test",
                "datasets": ["mmlu_sample_100.jsonl"],
                "models": ["llama-3.1-8b-instant"],
                "type": "mmlu",
                "limit": 10
            },
            "mmlu_full": {
                "name": "MMLU Full Test",
                "datasets": ["mmlu_sample_100.jsonl", "mmlu_multi_category_250.jsonl"],
                "models": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
                "type": "mmlu",
                "limit": None
            },
            "consciousness": {
                "name": "S2 Consciousness Tests",
                "datasets": [
                    "consciousness_tests/egregore_collaboration_tests.jsonl",
                    "consciousness_tests/deep_key_presence_tests.jsonl"
                ],
                "models": ["llama-3.3-70b-versatile"],
                "type": "consciousness",
                "limit": None
            },
            "speed_test": {
                "name": "Groq Speed Comparison",
                "datasets": ["mmlu_sample_100.jsonl"],
                "models": [
                    "llama-3.1-8b-instant",
                    "llama-3.3-70b-versatile",
                    "mixtral-8x7b-32768"
                ],
                "type": "mmlu",
                "limit": 20
            }
        }
    
    def run_suite(self, suite_name: str) -> List[Dict[str, Any]]:
        """Run a benchmark suite"""
        
        if suite_name not in self.suites:
            raise ValueError(f"Unknown suite: {suite_name}")
        
        suite = self.suites[suite_name]
        
        print(f"\n🎯 Running Suite: {suite['name']}")
        print("=" * 60)
        
        all_results = []
        
        for dataset in suite["datasets"]:
            for model in suite["models"]:
                print(f"\n📊 {dataset} with {model}")
                
                try:
                    if suite["type"] == "mmlu":
                        result = self.runner.run_mmlu_benchmark(
                            dataset,
                            model,
                            limit=suite.get("limit")
                        )
                    else:
                        result = self.runner.run_consciousness_benchmark(
                            dataset,
                            model
                        )
                    
                    all_results.append(result)
                    
                except FileNotFoundError as e:
                    print(f"⚠️ Skipping {dataset}: {e}")
                    continue
                except Exception as e:
                    print(f"❌ Error: {e}")
                    continue
        
        # Save suite summary
        self._save_suite_summary(suite_name, all_results)
        
        return all_results
    
    def run_all_suites(self):
        """Run all benchmark suites"""
        
        print("\n🌟 Running All Benchmark Suites")
        print("=" * 60)
        
        suite_results = {}
        
        for suite_name in self.suites:
            print(f"\n{'='*60}")
            print(f"Suite: {suite_name}")
            print(f"{'='*60}")
            
            results = self.run_suite(suite_name)
            suite_results[suite_name] = results
        
        # Final summary
        self._print_final_summary(suite_results)
        
        return suite_results
    
    def _save_suite_summary(self, suite_name: str, results: List[Dict[str, Any]]):
        """Save suite summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"suite_{suite_name}_{timestamp}.json"
        
        summary = {
            "suite_name": suite_name,
            "suite_config": self.suites[suite_name],
            "timestamp": timestamp,
            "num_results": len(results),
            "results": results
        }
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n💾 Suite summary: {filename}")
    
    def _print_final_summary(self, suite_results: Dict[str, List[Dict[str, Any]]]):
        """Print final summary"""
        print("\n\n" + "="*60)
        print("🎉 ALL SUITES COMPLETE")
        print("="*60)
        
        for suite_name, results in suite_results.items():
            print(f"\n{suite_name}:")
            print(f"  Tests run: {len(results)}")
            
            if results and "accuracy" in results[0]:
                avg_acc = sum(r["accuracy"] for r in results) / len(results)
                print(f"  Avg Accuracy: {avg_acc*100:.2f}%")
            
            if results and "average_score" in results[0]:
                avg_score = sum(r["average_score"] for r in results) / len(results)
                print(f"  Avg Score: {avg_score:.2f}")
        
        print(f"\n📁 All results saved to: {self.results_dir}/")

def main():
    """Run orchestrator"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Groq Benchmark Orchestrator")
    parser.add_argument("--suite", help="Specific suite to run")
    parser.add_argument("--all", action="store_true", help="Run all suites")
    parser.add_argument("--list", action="store_true", help="List available suites")
    
    args = parser.parse_args()
    
    orchestrator = GroqBenchmarkSuite()
    
    if args.list:
        print("\n📋 Available Suites:")
        for name, config in orchestrator.suites.items():
            print(f"\n  {name}")
            print(f"    {config['name']}")
            print(f"    Datasets: {len(config['datasets'])}")
            print(f"    Models: {len(config['models'])}")
        return
    
    if args.all:
        orchestrator.run_all_suites()
    elif args.suite:
        orchestrator.run_suite(args.suite)
    else:
        print("Usage:")
        print("  --list           List available suites")
        print("  --suite NAME     Run specific suite")
        print("  --all            Run all suites")
        print("\nExample:")
        print("  python groq_orchestrator.py --suite mmlu_pilot")

if __name__ == "__main__":
    main()
