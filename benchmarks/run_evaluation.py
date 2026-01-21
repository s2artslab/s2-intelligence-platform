#!/usr/bin/env python3
"""
Run Benchmark Evaluation
Executes MMLU benchmark evaluation using Together.ai
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    import together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False
    print("⚠️ Together SDK not installed. Run: pip install together")

class BenchmarkEvaluator:
    """Handles benchmark evaluation workflow"""
    
    def __init__(self):
        self.api_key = os.getenv("TOGETHER_API_KEY")
        if self.api_key and TOGETHER_AVAILABLE:
            together.api_key = self.api_key
        
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
    
    def load_file_id(self, dataset_file: str) -> Optional[str]:
        """Load file ID from saved file"""
        file_id_path = f"{dataset_file}.file_id"
        
        if Path(file_id_path).exists():
            with open(file_id_path, "r") as f:
                file_id = f.read().strip()
                print(f"📝 Loaded File ID: {file_id}")
                return file_id
        
        print(f"⚠️ File ID not found: {file_id_path}")
        print(f"   Run: python upload_dataset.py")
        return None
    
    def create_evaluation(
        self,
        dataset_file_id: str,
        model: str = "meta-llama/Llama-3.1-8B-Instruct-Turbo",
        judge_model: str = "meta-llama/Llama-3.1-70B-Instruct-Turbo",
        evaluation_name: str = "S2 MMLU Pilot"
    ) -> Optional[str]:
        """Create evaluation on Together.ai"""
        
        if not TOGETHER_AVAILABLE or not self.api_key:
            print("❌ Together.ai not configured")
            return None
        
        print(f"\n🚀 Creating Evaluation: {evaluation_name}")
        print("=" * 60)
        print(f"📊 Model: {model}")
        print(f"⚖️ Judge: {judge_model}")
        print(f"📄 Dataset: {dataset_file_id}")
        
        try:
            # Create evaluation
            evaluation = together.Evaluations.create(
                mode="classify",
                model=model,
                dataset_file_id=dataset_file_id,
                judge_model=judge_model,
                judge_system_template="""You are evaluating an AI model's answer to a multiple-choice question.
The model should respond with ONLY a letter (A, B, C, or D).
Extract the letter from the model's response.
If the model gave a valid answer letter, respond with that letter.
If unclear or multiple letters, respond with 'UNCLEAR'.""",
                judge_input_template="""Question: {{prompt}}

Model's Answer: {{output}}

Which choice did the model select? Respond with ONLY the letter (A, B, C, or D):""",
                labels=["A", "B", "C", "D", "UNCLEAR"]
            )
            
            print(f"\n✅ Evaluation Created!")
            print(f"📝 Evaluation ID: {evaluation.id}")
            print(f"⏳ Status: {evaluation.status}")
            
            return evaluation.id
            
        except Exception as e:
            print(f"❌ Failed to create evaluation: {e}")
            return None
    
    def poll_evaluation(self, evaluation_id: str, poll_interval: int = 10) -> Optional[Dict[str, Any]]:
        """Poll evaluation until completion"""
        
        if not TOGETHER_AVAILABLE or not self.api_key:
            print("❌ Together.ai not configured")
            return None
        
        print(f"\n⏳ Monitoring Evaluation: {evaluation_id}")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            while True:
                status = together.Evaluations.retrieve(evaluation_id)
                
                elapsed = int(time.time() - start_time)
                elapsed_str = f"{elapsed//60}m {elapsed%60}s"
                
                print(f"   [{elapsed_str}] Status: {status.status}")
                
                if status.status == "completed":
                    print(f"\n✅ Evaluation Complete!")
                    print(f"⏱️ Total Time: {elapsed_str}")
                    return status.results
                
                elif status.status == "failed":
                    print(f"\n❌ Evaluation Failed")
                    if hasattr(status, 'error'):
                        print(f"   Error: {status.error}")
                    return None
                
                elif status.status == "cancelled":
                    print(f"\n⚠️ Evaluation Cancelled")
                    return None
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print(f"\n\n⚠️ Monitoring interrupted")
            print(f"   Evaluation ID: {evaluation_id}")
            print(f"   Check status: python run_evaluation.py check {evaluation_id}")
            return None
        
        except Exception as e:
            print(f"❌ Polling error: {e}")
            return None
    
    def save_results(self, evaluation_id: str, results: Dict[str, Any], dataset_name: str):
        """Save evaluation results"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"eval_{dataset_name}_{timestamp}.json"
        
        output = {
            "evaluation_id": evaluation_id,
            "dataset": dataset_name,
            "timestamp": timestamp,
            "results": results
        }
        
        with open(results_file, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Results saved: {results_file}")
        return results_file
    
    def analyze_results(self, results: Dict[str, Any], dataset_file: str):
        """Analyze and display evaluation results"""
        
        print(f"\n📊 Results Analysis")
        print("=" * 60)
        
        total = results.get('total_items', 0)
        print(f"Total Questions: {total}")
        
        # Load original dataset to calculate accuracy
        if Path(dataset_file).exists():
            with open(dataset_file, 'r') as f:
                questions = [json.loads(line) for line in f]
            
            # Parse detailed results if available
            if 'detailed_results' in results:
                correct = 0
                unclear = 0
                wrong = 0
                
                for i, detail in enumerate(results['detailed_results'][:total]):
                    model_answer = detail.get('classification', 'UNCLEAR')
                    correct_answer = questions[i]['reference_answer']
                    
                    if model_answer == correct_answer:
                        correct += 1
                    elif model_answer == 'UNCLEAR':
                        unclear += 1
                    else:
                        wrong += 1
                
                accuracy = (correct / total * 100) if total > 0 else 0
                
                print(f"\nCorrect: {correct} ({correct/total*100:.1f}%)")
                print(f"Wrong: {wrong} ({wrong/total*100:.1f}%)")
                print(f"Unclear: {unclear} ({unclear/total*100:.1f}%)")
                print(f"\n✨ ACCURACY: {accuracy:.2f}%")
                
                # Compare to benchmarks
                print(f"\n📈 Comparison to Public Benchmarks:")
                print("-" * 60)
                print(f"GPT-5.2 (MMLU):     ~85%")
                print(f"Claude 4 Opus:      ~86-89%")
                print(f"Gemini 3 Pro:       ~88%")
                print(f"Llama 3.1 8B:       ~68%")
                print(f"Llama 3.1 70B:      ~76%")
                print(f"\nS2 Intelligence:    {accuracy:.2f}% (pilot)")
                print("-" * 60)
                
                if accuracy >= 80:
                    print("\n🌟 EXCELLENT! Top-tier performance!")
                elif accuracy >= 70:
                    print("\n✅ GOOD! Competitive performance!")
                elif accuracy >= 60:
                    print("\n⚠️ MODERATE. Room for improvement.")
                else:
                    print("\n❌ LOW. Needs investigation.")
        
        elif 'classification_results' in results:
            # Fallback: show label distribution
            print("\n📊 Label Distribution:")
            for label, count in results['classification_results'].items():
                print(f"   {label}: {count}")
    
    def run_full_evaluation(
        self,
        dataset_file: str,
        model: str = "meta-llama/Llama-3.1-8B-Instruct-Turbo",
        evaluation_name: str = "S2 MMLU Pilot"
    ):
        """Run complete evaluation workflow"""
        
        print(f"🔬 S2 Intelligence Benchmark Evaluation")
        print("=" * 60)
        print(f"📄 Dataset: {dataset_file}")
        print(f"🤖 Model: {model}")
        
        # Load file ID
        file_id = self.load_file_id(dataset_file)
        if not file_id:
            return False
        
        # Create evaluation
        eval_id = self.create_evaluation(file_id, model, evaluation_name=evaluation_name)
        if not eval_id:
            return False
        
        # Poll for completion
        results = self.poll_evaluation(eval_id)
        if not results:
            return False
        
        # Save results
        results_file = self.save_results(eval_id, results, Path(dataset_file).stem)
        
        # Analyze results
        self.analyze_results(results, dataset_file)
        
        print(f"\n🎉 Evaluation Complete!")
        print(f"\n📊 Next steps:")
        print(f"1. Review results: {results_file}")
        print(f"2. Run on larger dataset")
        print(f"3. Test S2 Intelligence custom model")
        
        return True

def check_evaluation_status(evaluation_id: str):
    """Check status of existing evaluation"""
    
    if not TOGETHER_AVAILABLE:
        print("❌ Together SDK not available")
        return
    
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("❌ TOGETHER_API_KEY not set")
        return
    
    together.api_key = api_key
    
    try:
        status = together.Evaluations.retrieve(evaluation_id)
        
        print(f"\n📊 Evaluation Status: {evaluation_id}")
        print("=" * 60)
        print(f"Status: {status.status}")
        print(f"Created: {status.created_at}")
        
        if status.status == "completed":
            print("\n✅ Evaluation complete!")
            print(f"Results available: {status.results}")
        elif status.status == "failed":
            print(f"\n❌ Evaluation failed")
            if hasattr(status, 'error'):
                print(f"Error: {status.error}")
        
    except Exception as e:
        print(f"❌ Failed to check status: {e}")

if __name__ == "__main__":
    import sys
    
    evaluator = BenchmarkEvaluator()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "check" and len(sys.argv) > 2:
            check_evaluation_status(sys.argv[2])
        else:
            # Run evaluation on specified dataset
            dataset_file = sys.argv[1]
            model = sys.argv[2] if len(sys.argv) > 2 else "meta-llama/Llama-3.1-8B-Instruct-Turbo"
            evaluator.run_full_evaluation(dataset_file, model)
    else:
        # Default: run pilot evaluation
        print("🚀 Running Default Pilot Evaluation")
        print("=" * 60)
        
        dataset_file = "mmlu_sample_100.jsonl"
        
        if not Path(dataset_file).exists():
            print(f"❌ Dataset not found: {dataset_file}")
            print(f"\n📥 Please run: python download_mmlu_sample.py")
        else:
            evaluator.run_full_evaluation(dataset_file)
