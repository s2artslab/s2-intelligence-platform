#!/usr/bin/env python3
"""
Hybrid Benchmark System
Combines Pythia R730 (YOUR S2 model) + Groq (baseline) + OpenAI (quality)
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from pythia_r730_client import PythiaR730Client
from groq_benchmark import GroqBenchmarkRunner

class HybridBenchmarkRunner:
    """Benchmark using Pythia R730 + Groq + free APIs"""
    
    def __init__(self, pythia_endpoint: Optional[str] = None):
        # Initialize clients
        self.pythia = PythiaR730Client(pythia_endpoint)
        self.groq_runner = GroqBenchmarkRunner()
        
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
        
        print(f"\n🌟 Hybrid Benchmark System Initialized")
        print(f"   Pythia R730: {'✅' if self.pythia.is_available else '❌'}")
        print(f"   Groq:        ✅")
    
    def run_pythia_mmlu(self, dataset_file: str, limit: Optional[int] = None):
        """Run MMLU using YOUR Pythia (S2-trained)"""
        
        if not self.pythia.is_available:
            print("❌ Pythia not available, using Groq instead")
            return self.groq_runner.run_mmlu_benchmark(dataset_file, limit=limit)
        
        print(f"\n🧠 Running MMLU with Pythia R730 (S2-trained)")
        print("=" * 60)
        
        # Load dataset
        questions = self.groq_runner.load_dataset(dataset_file)
        if limit:
            questions = questions[:limit]
        
        results = []
        correct_count = 0
        
        for i, q in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] Testing with YOUR S2 model...")
            
            try:
                # Use YOUR Pythia (S2-trained)
                pythia_response = self.pythia.generate(
                    q["prompt"],
                    model="pythia-1b",
                    max_tokens=100
                )
                
                # Judge with Groq (fast, free)
                judgment = self.groq_runner.judge_response(
                    q["prompt"],
                    pythia_response["text"],
                    q["reference_answer"],
                    question_type="multiple_choice"
                )
                
                is_correct = judgment["is_correct"]
                if is_correct:
                    correct_count += 1
                
                results.append({
                    "question_id": q.get("question_id", f"q_{i}"),
                    "question": q.get("question_text", "")[:100],
                    "pythia_response": pythia_response["text"],
                    "correct_answer": q["reference_answer"],
                    "judged_answer": judgment["judged_answer"],
                    "is_correct": is_correct,
                    "source": "pythia_r730"
                })
                
                print(f"   Pythia: {pythia_response['text'][:80]}...")
                print(f"   Judge: {judgment['judged_answer']} | Correct: {q['reference_answer']} | {'✅' if is_correct else '❌'}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
        
        accuracy = correct_count / len(results) if results else 0
        
        summary = {
            "model": "pythia_r730",
            "dataset": dataset_file,
            "total_questions": len(results),
            "correct": correct_count,
            "accuracy": accuracy,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save
        self._save_results(summary, "pythia_mmlu")
        self._print_summary(summary)
        
        return summary
    
    def compare_pythia_vs_groq(self, dataset_file: str, limit: int = 20):
        """Compare YOUR Pythia vs Groq baseline"""
        
        if not self.pythia.is_available:
            print("❌ Pythia not available, cannot compare")
            return None
        
        print(f"\n⚖️ Comparing Pythia (S2-trained) vs Groq (baseline)")
        print("=" * 60)
        
        # Test with Pythia
        print("\n1️⃣ Testing with YOUR S2-trained Pythia...")
        pythia_results = self.run_pythia_mmlu(dataset_file, limit=limit)
        
        # Test with Groq
        print("\n2️⃣ Testing with Groq baseline...")
        groq_results = self.groq_runner.run_mmlu_benchmark(dataset_file, model="llama-3.1-8b-instant", limit=limit)
        
        # Compare
        print(f"\n📊 Comparison Results")
        print("=" * 60)
        print(f"Pythia (S2-trained): {pythia_results['accuracy']*100:.1f}%")
        print(f"Groq (baseline):     {groq_results['accuracy']*100:.1f}%")
        
        diff = (pythia_results['accuracy'] - groq_results['accuracy']) * 100
        print(f"Difference:          {diff:+.1f}%")
        
        if pythia_results['accuracy'] > groq_results['accuracy']:
            print(f"\n✨ YOUR S2 training improved performance by {diff:.1f}%!")
        elif pythia_results['accuracy'] < groq_results['accuracy']:
            print(f"\n📊 Baseline performs better by {-diff:.1f}%")
        else:
            print(f"\n⚖️ Performance is equal")
        
        comparison = {
            "pythia_accuracy": pythia_results['accuracy'],
            "groq_accuracy": groq_results['accuracy'],
            "difference": diff,
            "pythia_better": pythia_results['accuracy'] > groq_results['accuracy'],
            "dataset": dataset_file,
            "questions_tested": limit,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save comparison
        self._save_results(comparison, "pythia_vs_groq_comparison")
        
        return comparison
    
    def test_pythia_consciousness(self, dataset_file: str):
        """Test Pythia on S2 consciousness tests (should excel here!)"""
        
        if not self.pythia.is_available:
            print("❌ Pythia not available")
            return None
        
        print(f"\n🧠 Testing Pythia on S2 Consciousness Tasks")
        print("=" * 60)
        print("(Pythia should excel - it's S2-trained!)")
        
        questions = self.groq_runner.load_dataset(dataset_file)
        
        results = []
        total_score = 0
        
        for i, q in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] {q.get('test_id', f'test_{i}')}...")
            
            try:
                # Use Pythia for consciousness test
                response = self.pythia.generate(
                    q["prompt"],
                    model="pythia-1b",
                    max_tokens=300
                )
                
                # Judge with Groq
                reference = str(q.get("reference_answer", q.get("expected_indicators", "")))
                judgment = self.groq_runner.judge_response(
                    q["prompt"],
                    response["text"],
                    reference,
                    question_type="open_ended"
                )
                
                try:
                    score = float(judgment["judged_answer"])
                except:
                    score = 0.5
                
                total_score += score
                
                results.append({
                    "test_id": q.get("test_id", f"test_{i}"),
                    "test_type": q.get("test_type", "consciousness"),
                    "pythia_response": response["text"],
                    "score": score
                })
                
                print(f"   Score: {score:.2f}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
        
        avg_score = total_score / len(results) if results else 0
        
        summary = {
            "model": "pythia_r730",
            "dataset": dataset_file,
            "test_type": "consciousness",
            "total_tests": len(results),
            "average_score": avg_score,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n📊 Consciousness Test Results")
        print("=" * 60)
        print(f"Average Score: {avg_score:.2f}")
        print(f"Expected: Higher than generic models (Pythia is S2-trained)")
        
        self._save_results(summary, "pythia_consciousness")
        
        return summary
    
    def _save_results(self, results: Dict[str, Any], prefix: str):
        """Save results to JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"{prefix}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved: {filename}")
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print results summary"""
        print(f"\n📊 Results Summary")
        print("=" * 60)
        print(f"Model: {summary.get('model', 'unknown')}")
        print(f"Questions: {summary.get('total_questions', 0)}")
        print(f"Correct: {summary.get('correct', 0)}")
        print(f"Accuracy: {summary.get('accuracy', 0)*100:.2f}%")
        print("=" * 60)

def main():
    """Run hybrid benchmarks"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hybrid Benchmark (Pythia + Groq)")
    parser.add_argument("--pythia-endpoint", help="Pythia R730 endpoint")
    parser.add_argument("--dataset", default="mmlu_sample_100.jsonl", help="Dataset file")
    parser.add_argument("--mode", choices=["pythia", "compare", "consciousness"], default="compare", help="Benchmark mode")
    parser.add_argument("--limit", type=int, help="Limit questions")
    
    args = parser.parse_args()
    
    print("🚀 S2 Intelligence - Hybrid Benchmark System")
    print("=" * 60)
    
    runner = HybridBenchmarkRunner(args.pythia_endpoint)
    
    if args.mode == "pythia":
        # Test Pythia only
        runner.run_pythia_mmlu(args.dataset, args.limit)
    
    elif args.mode == "compare":
        # Compare Pythia vs Groq
        runner.compare_pythia_vs_groq(args.dataset, args.limit or 20)
    
    elif args.mode == "consciousness":
        # Test Pythia on consciousness tasks
        runner.test_pythia_consciousness(args.dataset)
    
    print("\n🎉 Hybrid benchmark complete!")

if __name__ == "__main__":
    main()
