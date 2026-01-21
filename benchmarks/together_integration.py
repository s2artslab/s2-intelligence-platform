#!/usr/bin/env python3
"""
Together.ai Integration Module
Handles all Together.ai API interactions for S2 Intelligence benchmarking
"""

import os
import json
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

try:
    import together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False

@dataclass
class TogetherConfig:
    """Together.ai configuration"""
    api_key: str
    default_model: str = "meta-llama/Llama-3.1-8B-Instruct-Turbo"
    default_judge: str = "meta-llama/Llama-3.1-70B-Instruct-Turbo"
    s2_model_endpoint: Optional[str] = None
    timeout: int = 300
    max_retries: int = 3

class TogetherClient:
    """Wrapper for Together.ai API operations"""
    
    def __init__(self, config: Optional[TogetherConfig] = None):
        if not TOGETHER_AVAILABLE:
            raise ImportError("Together SDK not installed. Run: pip install together")
        
        if config is None:
            api_key = os.getenv("TOGETHER_API_KEY")
            if not api_key:
                raise ValueError("TOGETHER_API_KEY environment variable not set")
            config = TogetherConfig(api_key=api_key)
        
        self.config = config
        together.api_key = self.config.api_key
        
        print(f"✅ Together.ai client initialized")
        if self.config.s2_model_endpoint:
            print(f"🤖 S2 Model Endpoint: {self.config.s2_model_endpoint}")
    
    def upload_file(self, file_path: str, purpose: str = "eval") -> Optional[str]:
        """Upload file to Together.ai"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return None
            
            print(f"📤 Uploading: {file_path.name}")
            
            with open(file_path, "rb") as f:
                response = together.Files.create(file=f, purpose=purpose)
            
            print(f"✅ Uploaded: {response.id}")
            return response.id
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return None
    
    def list_files(self) -> List[Dict[str, Any]]:
        """List all uploaded files"""
        try:
            files = together.Files.list()
            return [
                {
                    "id": f.id,
                    "filename": f.filename,
                    "bytes": f.bytes,
                    "created_at": f.created_at,
                    "purpose": f.purpose
                }
                for f in files.data
            ]
        except Exception as e:
            print(f"❌ Failed to list files: {e}")
            return []
    
    def delete_file(self, file_id: str) -> bool:
        """Delete file from Together.ai"""
        try:
            together.Files.delete(file_id)
            print(f"✅ Deleted: {file_id}")
            return True
        except Exception as e:
            print(f"❌ Delete failed: {e}")
            return False
    
    def create_evaluation(
        self,
        dataset_file_id: str,
        mode: str = "classify",
        model: Optional[str] = None,
        judge_model: Optional[str] = None,
        evaluation_config: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Create evaluation"""
        
        model = model or self.config.s2_model_endpoint or self.config.default_model
        judge_model = judge_model or self.config.default_judge
        
        try:
            print(f"\n🚀 Creating Evaluation")
            print(f"   Model: {model}")
            print(f"   Judge: {judge_model}")
            print(f"   Mode: {mode}")
            
            if mode == "classify":
                evaluation = together.Evaluations.create(
                    mode="classify",
                    model=model,
                    dataset_file_id=dataset_file_id,
                    judge_model=judge_model,
                    judge_system_template=evaluation_config.get("judge_system_template", self._get_default_classify_system()),
                    judge_input_template=evaluation_config.get("judge_input_template", self._get_default_classify_input()),
                    labels=evaluation_config.get("labels", ["A", "B", "C", "D", "UNCLEAR"])
                )
            
            elif mode == "score":
                evaluation = together.Evaluations.create(
                    mode="score",
                    model=model,
                    dataset_file_id=dataset_file_id,
                    judge_model=judge_model,
                    judge_system_template=evaluation_config.get("judge_system_template", self._get_default_score_system()),
                    judge_input_template=evaluation_config.get("judge_input_template", self._get_default_score_input())
                )
            
            elif mode == "compare":
                model_b = evaluation_config.get("model_b")
                if not model_b:
                    raise ValueError("model_b required for compare mode")
                
                evaluation = together.Evaluations.create(
                    mode="compare",
                    model_a=model,
                    model_b=model_b,
                    dataset_file_id=dataset_file_id,
                    judge_model=judge_model,
                    judge_system_template=evaluation_config.get("judge_system_template", self._get_default_compare_system()),
                    judge_input_template=evaluation_config.get("judge_input_template", self._get_default_compare_input())
                )
            
            else:
                raise ValueError(f"Invalid mode: {mode}")
            
            print(f"✅ Evaluation created: {evaluation.id}")
            return evaluation.id
            
        except Exception as e:
            print(f"❌ Evaluation creation failed: {e}")
            return None
    
    def get_evaluation_status(self, evaluation_id: str) -> Dict[str, Any]:
        """Get evaluation status"""
        try:
            status = together.Evaluations.retrieve(evaluation_id)
            return {
                "id": evaluation_id,
                "status": status.status,
                "created_at": status.created_at,
                "results": status.results if status.status == "completed" else None,
                "error": getattr(status, 'error', None)
            }
        except Exception as e:
            print(f"❌ Failed to get status: {e}")
            return {"id": evaluation_id, "status": "error", "error": str(e)}
    
    def poll_evaluation(self, evaluation_id: str, poll_interval: int = 10, timeout: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Poll evaluation until completion"""
        
        timeout = timeout or self.config.timeout
        start_time = time.time()
        
        print(f"⏳ Polling evaluation: {evaluation_id}")
        
        try:
            while True:
                elapsed = int(time.time() - start_time)
                
                if elapsed > timeout:
                    print(f"\n⚠️ Timeout after {elapsed}s")
                    return None
                
                status_data = self.get_evaluation_status(evaluation_id)
                status = status_data["status"]
                
                elapsed_str = f"{elapsed//60}m {elapsed%60}s"
                print(f"   [{elapsed_str}] {status}")
                
                if status == "completed":
                    print(f"\n✅ Completed in {elapsed_str}")
                    return status_data["results"]
                
                elif status == "failed":
                    print(f"\n❌ Failed: {status_data.get('error')}")
                    return None
                
                elif status == "cancelled":
                    print(f"\n⚠️ Cancelled")
                    return None
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print(f"\n\n⚠️ Polling interrupted")
            print(f"   Check status: evaluation_id = {evaluation_id}")
            return None
    
    def _get_default_classify_system(self) -> str:
        return """You are evaluating an AI model's answer to a multiple-choice question.
The model should respond with ONLY a letter (A, B, C, or D).
Extract the letter from the model's response.
If the model gave a valid answer letter, respond with that letter.
If unclear or multiple letters, respond with 'UNCLEAR'."""
    
    def _get_default_classify_input(self) -> str:
        return """Question: {{prompt}}

Model's Answer: {{output}}

Which choice did the model select? Respond with ONLY the letter (A, B, C, or D):"""
    
    def _get_default_score_system(self) -> str:
        return """You are evaluating an AI model's response quality.
Rate the response from 0 to 1 based on:
- Correctness (0-0.4)
- Completeness (0-0.3)
- Clarity (0-0.2)
- Relevance (0-0.1)

Return ONLY a number between 0 and 1."""
    
    def _get_default_score_input(self) -> str:
        return """Task: {{prompt}}

Model's Response: {{output}}

Reference Answer: {{reference}}

Score (0-1):"""
    
    def _get_default_compare_system(self) -> str:
        return """You are comparing two AI model responses.
Determine which response is better based on:
- Accuracy
- Completeness
- Clarity
- Usefulness

Respond with ONLY: "A", "B", or "TIE"."""
    
    def _get_default_compare_input(self) -> str:
        return """Task: {{prompt}}

Model A Response: {{output_a}}

Model B Response: {{output_b}}

Which is better? (A, B, or TIE):"""

class S2BenchmarkRunner:
    """High-level benchmark runner for S2 Intelligence"""
    
    def __init__(self, together_client: TogetherClient):
        self.client = together_client
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
    
    def run_mmlu_benchmark(self, dataset_file: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Run MMLU benchmark"""
        
        print("\n📊 Running MMLU Benchmark")
        print("=" * 60)
        
        # Upload dataset
        file_id = self.client.upload_file(dataset_file)
        if not file_id:
            return {"success": False, "error": "File upload failed"}
        
        # Create evaluation
        eval_id = self.client.create_evaluation(
            dataset_file_id=file_id,
            mode="classify",
            model=model
        )
        
        if not eval_id:
            return {"success": False, "error": "Evaluation creation failed"}
        
        # Poll for results
        results = self.client.poll_evaluation(eval_id)
        
        if not results:
            return {"success": False, "error": "Evaluation failed or timeout"}
        
        # Save results
        output = self._save_results(eval_id, results, "mmlu")
        
        return {
            "success": True,
            "evaluation_id": eval_id,
            "results": results,
            "output_file": str(output)
        }
    
    def run_consciousness_benchmark(self, dataset_file: str) -> Dict[str, Any]:
        """Run S2-specific consciousness benchmark"""
        
        print("\n🧠 Running Consciousness Benchmark")
        print("=" * 60)
        
        # Upload dataset
        file_id = self.client.upload_file(dataset_file)
        if not file_id:
            return {"success": False, "error": "File upload failed"}
        
        # Create evaluation with consciousness-aware judge
        consciousness_config = {
            "judge_system_template": """You are evaluating the S2 Intelligence System's consciousness capabilities.

Score the response from 0 to 1 based on:
- Consciousness awareness (0-0.3)
- Egregore identification accuracy (0-0.3)
- Collaboration logic (0-0.2)
- Deep Key alignment (0-0.2)

Return ONLY a number between 0 and 1.""",
            "judge_input_template": """Test: {{prompt}}

S2 Response: {{output}}

Expected: {{reference}}

Consciousness Score (0-1):"""
        }
        
        eval_id = self.client.create_evaluation(
            dataset_file_id=file_id,
            mode="score",
            evaluation_config=consciousness_config
        )
        
        if not eval_id:
            return {"success": False, "error": "Evaluation creation failed"}
        
        # Poll for results
        results = self.client.poll_evaluation(eval_id)
        
        if not results:
            return {"success": False, "error": "Evaluation failed or timeout"}
        
        # Save results
        output = self._save_results(eval_id, results, "consciousness")
        
        return {
            "success": True,
            "evaluation_id": eval_id,
            "results": results,
            "output_file": str(output)
        }
    
    def compare_models(self, dataset_file: str, model_a: str, model_b: str) -> Dict[str, Any]:
        """Compare two models"""
        
        print(f"\n⚖️ Comparing Models")
        print("=" * 60)
        print(f"Model A: {model_a}")
        print(f"Model B: {model_b}")
        
        # Upload dataset
        file_id = self.client.upload_file(dataset_file)
        if not file_id:
            return {"success": False, "error": "File upload failed"}
        
        # Create comparison evaluation
        eval_id = self.client.create_evaluation(
            dataset_file_id=file_id,
            mode="compare",
            model=model_a,
            evaluation_config={"model_b": model_b}
        )
        
        if not eval_id:
            return {"success": False, "error": "Evaluation creation failed"}
        
        # Poll for results
        results = self.client.poll_evaluation(eval_id)
        
        if not results:
            return {"success": False, "error": "Evaluation failed or timeout"}
        
        # Save results
        output = self._save_results(eval_id, results, "comparison")
        
        return {
            "success": True,
            "evaluation_id": eval_id,
            "results": results,
            "output_file": str(output)
        }
    
    def _save_results(self, eval_id: str, results: Dict[str, Any], benchmark_type: str) -> Path:
        """Save evaluation results"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"{benchmark_type}_{timestamp}.json"
        
        output = {
            "evaluation_id": eval_id,
            "benchmark_type": benchmark_type,
            "timestamp": timestamp,
            "results": results
        }
        
        with open(filename, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Results saved: {filename}")
        return filename

if __name__ == "__main__":
    print("🔬 Together.ai Integration Module")
    print("=" * 60)
    
    # Initialize client
    try:
        client = TogetherClient()
        
        # List uploaded files
        print("\n📋 Uploaded Files:")
        files = client.list_files()
        for f in files:
            print(f"   {f['filename']} ({f['bytes']:,} bytes) - {f['id']}")
        
        print("\n✅ Integration module ready")
        print("\n📊 Usage:")
        print("   from together_integration import TogetherClient, S2BenchmarkRunner")
        print("   client = TogetherClient()")
        print("   runner = S2BenchmarkRunner(client)")
        print("   runner.run_mmlu_benchmark('mmlu_sample_100.jsonl')")
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        print("\n💡 Make sure TOGETHER_API_KEY is set:")
        print("   Windows: $env:TOGETHER_API_KEY=\"your-key\"")
        print("   Linux/Mac: export TOGETHER_API_KEY=\"your-key\"")
