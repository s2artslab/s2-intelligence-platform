#!/usr/bin/env python3
"""
S2 Intelligence Groq Benchmark System
Main benchmark runner using Groq API + free judge systems
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("❌ Groq SDK not installed. Run: pip install groq")

@dataclass
class BenchmarkResult:
    """Single benchmark result"""
    question_id: str
    question: str
    model_response: str
    correct_answer: str
    judged_answer: str
    is_correct: bool
    latency: float
    tokens_used: int

class GroqBenchmarkRunner:
    """Benchmark runner using Groq API"""
    
    def __init__(self, api_key: Optional[str] = None, judge_model: str = "llama-3.3-70b-versatile"):
        if not GROQ_AVAILABLE:
            raise ImportError("Groq SDK required. Run: pip install groq")
        
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set")
        
        self.client = Groq(api_key=self.api_key)
        self.judge_model = judge_model
        
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
        
        self.datasets_dir = Path("datasets")
        self.datasets_dir.mkdir(exist_ok=True)
        
        print(f"✅ Groq Benchmark Runner initialized")
        print(f"   Judge Model: {self.judge_model}")
    
    def load_dataset(self, dataset_file: str) -> List[Dict[str, Any]]:
        """Load dataset from JSONL file"""
        dataset_path = self.datasets_dir / dataset_file
        
        if not dataset_path.exists():
            # Try root directory
            dataset_path = Path(dataset_file)
        
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found: {dataset_file}")
        
        questions = []
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                questions.append(json.loads(line))
        
        print(f"📄 Loaded {len(questions)} questions from {dataset_file}")
        return questions
    
    def get_model_response(
        self,
        model: str,
        question: str,
        max_tokens: int = 100,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Get response from Groq model"""
        
        start_time = time.time()
        
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        latency = time.time() - start_time
        
        return {
            "text": response.choices[0].message.content,
            "latency": latency,
            "tokens": response.usage.total_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens
        }
    
    def judge_response(
        self,
        question: str,
        response: str,
        correct_answer: str,
        question_type: str = "multiple_choice"
    ) -> Dict[str, Any]:
        """Judge model response using Groq judge"""
        
        if question_type == "multiple_choice":
            judge_prompt = f"""You are evaluating an AI model's answer to a multiple-choice question.

Question: {question}

Model's Response: {response}

Correct Answer: {correct_answer}

Task: Extract ONLY the letter (A, B, C, or D) that the model selected. 
If the model's answer is unclear or contains multiple letters, respond with "UNCLEAR".
Respond with ONLY a single letter or "UNCLEAR".

Model's Answer Letter:"""
        
        else:  # Open-ended or consciousness tests
            judge_prompt = f"""Rate this AI response from 0.0 to 1.0:

Question: {question}

Model's Response: {response}

Expected/Reference: {correct_answer}

Scoring:
- 1.0 = Perfect, comprehensive answer
- 0.7-0.9 = Good answer, mostly correct
- 0.4-0.6 = Partial answer, some issues
- 0.1-0.3 = Poor answer, mostly incorrect
- 0.0 = Completely wrong or nonsense

Respond with ONLY a number between 0.0 and 1.0.

Score:"""
        
        judgment = self.client.chat.completions.create(
            model=self.judge_model,
            messages=[{"role": "user", "content": judge_prompt}],
            max_tokens=10,
            temperature=0.0
        )
        
        judged_answer = judgment.choices[0].message.content.strip()
        
        if question_type == "multiple_choice":
            is_correct = judged_answer == correct_answer
        else:
            try:
                score = float(judged_answer)
                is_correct = score >= 0.6  # Threshold for "correct"
            except:
                score = 0.0
                is_correct = False
        
        return {
            "judged_answer": judged_answer,
            "is_correct": is_correct,
            "raw_judgment": judgment.choices[0].message.content
        }
    
    def run_mmlu_benchmark(
        self,
        dataset_file: str,
        model: str = "llama-3.1-8b-instant",
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Run MMLU benchmark"""
        
        print(f"\n📊 Running MMLU Benchmark")
        print(f"   Dataset: {dataset_file}")
        print(f"   Model: {model}")
        print("=" * 60)
        
        # Load dataset
        questions = self.load_dataset(dataset_file)
        
        if limit:
            questions = questions[:limit]
            print(f"   Limited to: {limit} questions")
        
        results = []
        correct_count = 0
        total_latency = 0
        
        for i, q in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] Processing question {q.get('question_id', i)}...")
            
            # Get model response
            response = self.get_model_response(model, q['prompt'])
            
            # Judge response
            judgment = self.judge_response(
                q['prompt'],
                response['text'],
                q['reference_answer'],
                question_type="multiple_choice"
            )
            
            # Create result
            result = BenchmarkResult(
                question_id=q.get('question_id', f"q_{i}"),
                question=q.get('question_text', q['prompt'][:100]),
                model_response=response['text'],
                correct_answer=q['reference_answer'],
                judged_answer=judgment['judged_answer'],
                is_correct=judgment['is_correct'],
                latency=response['latency'],
                tokens_used=response['tokens']
            )
            
            results.append(result)
            
            if result.is_correct:
                correct_count += 1
            
            total_latency += response['latency']
            
            print(f"   Response: {response['text'][:80]}...")
            print(f"   Judged: {judgment['judged_answer']} | Correct: {q['reference_answer']} | {'✅' if result.is_correct else '❌'}")
            print(f"   Latency: {response['latency']:.3f}s")
        
        # Calculate metrics
        accuracy = correct_count / len(results) if results else 0
        avg_latency = total_latency / len(results) if results else 0
        
        summary = {
            "dataset": dataset_file,
            "model": model,
            "total_questions": len(results),
            "correct": correct_count,
            "accuracy": accuracy,
            "avg_latency": avg_latency,
            "timestamp": datetime.now().isoformat(),
            "results": [asdict(r) for r in results]
        }
        
        # Save results
        self._save_results(summary, f"mmlu_{model.replace('/', '_')}")
        
        # Print summary
        self._print_summary(summary)
        
        return summary
    
    def run_consciousness_benchmark(
        self,
        dataset_file: str,
        model: str = "llama-3.3-70b-versatile"
    ) -> Dict[str, Any]:
        """Run S2 consciousness benchmark"""
        
        print(f"\n🧠 Running Consciousness Benchmark")
        print(f"   Dataset: {dataset_file}")
        print(f"   Model: {model}")
        print("=" * 60)
        
        questions = self.load_dataset(dataset_file)
        
        results = []
        total_score = 0
        
        for i, q in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] Testing: {q.get('test_id', i)}...")
            
            # Get model response
            response = self.get_model_response(model, q['prompt'], max_tokens=300)
            
            # Judge with scoring (0-1)
            reference = q.get('reference_answer', q.get('expected_indicators', ''))
            if isinstance(reference, dict):
                reference = json.dumps(reference)
            elif isinstance(reference, list):
                reference = '; '.join(reference)
            
            judgment = self.judge_response(
                q['prompt'],
                response['text'],
                str(reference),
                question_type="open_ended"
            )
            
            try:
                score = float(judgment['judged_answer'])
            except:
                score = 0.0
            
            result = {
                "test_id": q.get('test_id', f"test_{i}"),
                "test_type": q.get('test_type', 'unknown'),
                "prompt": q['prompt'][:100] + "...",
                "response": response['text'],
                "score": score,
                "latency": response['latency']
            }
            
            results.append(result)
            total_score += score
            
            print(f"   Score: {score:.2f}")
        
        avg_score = total_score / len(results) if results else 0
        
        summary = {
            "dataset": dataset_file,
            "model": model,
            "total_tests": len(results),
            "average_score": avg_score,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        self._save_results(summary, f"consciousness_{model.replace('/', '_')}")
        self._print_consciousness_summary(summary)
        
        return summary
    
    def _save_results(self, results: Dict[str, Any], prefix: str):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"{prefix}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved: {filename}")
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print MMLU summary"""
        print(f"\n📊 MMLU Benchmark Results")
        print("=" * 60)
        print(f"Model: {summary['model']}")
        print(f"Questions: {summary['total_questions']}")
        print(f"Correct: {summary['correct']}")
        print(f"Accuracy: {summary['accuracy']*100:.2f}%")
        print(f"Avg Latency: {summary['avg_latency']:.3f}s")
        print("=" * 60)
        
        print(f"\n📈 Comparison to Benchmarks:")
        print(f"  GPT-5.2:     ~85%")
        print(f"  Claude 4:    ~87%")
        print(f"  Gemini 3:    ~88%")
        print(f"  Llama 70B:   ~76%")
        print(f"  Llama 8B:    ~68%")
        print(f"  This run:    {summary['accuracy']*100:.2f}%")
    
    def _print_consciousness_summary(self, summary: Dict[str, Any]):
        """Print consciousness summary"""
        print(f"\n🧠 Consciousness Benchmark Results")
        print("=" * 60)
        print(f"Model: {summary['model']}")
        print(f"Tests: {summary['total_tests']}")
        print(f"Average Score: {summary['average_score']:.2f}")
        print("=" * 60)

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="S2 Intelligence Groq Benchmark")
    parser.add_argument("--dataset", default="mmlu_sample_100.jsonl", help="Dataset file")
    parser.add_argument("--model", default="llama-3.1-8b-instant", help="Groq model to test")
    parser.add_argument("--type", choices=["mmlu", "consciousness"], default="mmlu", help="Benchmark type")
    parser.add_argument("--limit", type=int, help="Limit number of questions")
    parser.add_argument("--pilot", action="store_true", help="Run pilot (10 questions)")
    
    args = parser.parse_args()
    
    print("🚀 S2 Intelligence - Groq Benchmark System")
    print("=" * 60)
    
    if not os.getenv("GROQ_API_KEY"):
        print("❌ GROQ_API_KEY not set")
        print("   Set it: $env:GROQ_API_KEY=\"your-key\"")
        return
    
    runner = GroqBenchmarkRunner()
    
    limit = 10 if args.pilot else args.limit
    
    if args.type == "mmlu":
        runner.run_mmlu_benchmark(args.dataset, args.model, limit)
    else:
        runner.run_consciousness_benchmark(args.dataset, args.model)

if __name__ == "__main__":
    main()
