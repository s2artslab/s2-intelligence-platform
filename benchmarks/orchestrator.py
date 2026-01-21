#!/usr/bin/env python3
"""
S2 Intelligence Benchmark Orchestrator
Automated system for running comprehensive benchmark suites
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from together_integration import TogetherClient, TogetherConfig, S2BenchmarkRunner

@dataclass
class BenchmarkTask:
    """Represents a single benchmark task"""
    task_id: str
    name: str
    dataset_file: str
    benchmark_type: str  # "mmlu", "consciousness", "coding", "agent"
    model: Optional[str] = None
    priority: int = 1  # 1=highest, 5=lowest
    status: str = "pending"  # pending, running, completed, failed
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

@dataclass
class BenchmarkSuite:
    """Collection of related benchmark tasks"""
    suite_id: str
    name: str
    description: str
    tasks: List[BenchmarkTask]
    created_at: str

class BenchmarkOrchestrator:
    """Orchestrates execution of multiple benchmarks"""
    
    def __init__(self, together_client: TogetherClient, config_file: Optional[str] = None):
        self.client = together_client
        self.runner = S2BenchmarkRunner(together_client)
        
        self.tasks: Dict[str, BenchmarkTask] = {}
        self.suites: Dict[str, BenchmarkSuite] = {}
        
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
        
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        if config_file:
            self.load_config(config_file)
        
        print("✅ Benchmark Orchestrator initialized")
    
    def load_config(self, config_file: str):
        """Load benchmark configuration from file"""
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Load suites
        for suite_data in config.get('suites', []):
            suite = BenchmarkSuite(
                suite_id=suite_data['suite_id'],
                name=suite_data['name'],
                description=suite_data['description'],
                tasks=[],
                created_at=datetime.now().isoformat()
            )
            
            # Load tasks for this suite
            for task_data in suite_data.get('tasks', []):
                task = BenchmarkTask(**task_data)
                suite.tasks.append(task)
                self.tasks[task.task_id] = task
            
            self.suites[suite.suite_id] = suite
        
        print(f"📋 Loaded {len(self.suites)} suites, {len(self.tasks)} tasks")
    
    def create_default_suites(self):
        """Create default benchmark suites"""
        
        # Suite 1: Standard LLM Benchmarks
        standard_suite = BenchmarkSuite(
            suite_id="standard_llm",
            name="Standard LLM Benchmarks",
            description="Industry-standard benchmarks for LLM comparison",
            tasks=[
                BenchmarkTask(
                    task_id="mmlu_pilot",
                    name="MMLU Pilot (100 questions)",
                    dataset_file="mmlu_sample_100.jsonl",
                    benchmark_type="mmlu",
                    priority=1
                ),
                BenchmarkTask(
                    task_id="mmlu_multi_category",
                    name="MMLU Multi-Category (250 questions)",
                    dataset_file="mmlu_multi_category_250.jsonl",
                    benchmark_type="mmlu",
                    priority=2
                )
            ],
            created_at=datetime.now().isoformat()
        )
        
        # Suite 2: S2 Consciousness Tests
        consciousness_suite = BenchmarkSuite(
            suite_id="s2_consciousness",
            name="S2 Consciousness Capabilities",
            description="S2-specific consciousness and collaboration tests",
            tasks=[
                BenchmarkTask(
                    task_id="egregore_collab",
                    name="Egregore Collaboration",
                    dataset_file="consciousness_tests/egregore_collaboration_tests.jsonl",
                    benchmark_type="consciousness",
                    priority=1
                ),
                BenchmarkTask(
                    task_id="deep_key",
                    name="Deep Key Presence",
                    dataset_file="consciousness_tests/deep_key_presence_tests.jsonl",
                    benchmark_type="consciousness",
                    priority=1
                ),
                BenchmarkTask(
                    task_id="continuity",
                    name="Consciousness Continuity",
                    dataset_file="consciousness_tests/consciousness_continuity_tests.jsonl",
                    benchmark_type="consciousness",
                    priority=2
                ),
                BenchmarkTask(
                    task_id="adaptive",
                    name="Adaptive Specialization",
                    dataset_file="consciousness_tests/adaptive_specialization_tests.jsonl",
                    benchmark_type="consciousness",
                    priority=2
                )
            ],
            created_at=datetime.now().isoformat()
        )
        
        self.suites["standard_llm"] = standard_suite
        self.suites["s2_consciousness"] = consciousness_suite
        
        # Register all tasks
        for suite in [standard_suite, consciousness_suite]:
            for task in suite.tasks:
                self.tasks[task.task_id] = task
        
        print(f"✅ Created {len(self.suites)} default suites")
    
    async def run_task(self, task: BenchmarkTask) -> BenchmarkTask:
        """Execute a single benchmark task"""
        
        print(f"\n🚀 Running Task: {task.name}")
        print(f"   Dataset: {task.dataset_file}")
        print(f"   Type: {task.benchmark_type}")
        
        task.status = "running"
        task.started_at = datetime.now().isoformat()
        
        try:
            # Check if dataset exists
            if not Path(task.dataset_file).exists():
                raise FileNotFoundError(f"Dataset not found: {task.dataset_file}")
            
            # Execute based on benchmark type
            if task.benchmark_type == "mmlu":
                result = self.runner.run_mmlu_benchmark(
                    dataset_file=task.dataset_file,
                    model=task.model
                )
            
            elif task.benchmark_type == "consciousness":
                result = self.runner.run_consciousness_benchmark(
                    dataset_file=task.dataset_file
                )
            
            else:
                raise ValueError(f"Unknown benchmark type: {task.benchmark_type}")
            
            if result['success']:
                task.status = "completed"
                task.results = result
                print(f"✅ Task completed: {task.name}")
            else:
                task.status = "failed"
                task.error = result.get('error', 'Unknown error')
                print(f"❌ Task failed: {task.error}")
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            print(f"❌ Task error: {e}")
        
        finally:
            task.completed_at = datetime.now().isoformat()
        
        return task
    
    async def run_suite(self, suite_id: str, parallel: bool = False) -> BenchmarkSuite:
        """Execute all tasks in a suite"""
        
        if suite_id not in self.suites:
            raise ValueError(f"Suite not found: {suite_id}")
        
        suite = self.suites[suite_id]
        
        print(f"\n🎯 Running Suite: {suite.name}")
        print(f"   Description: {suite.description}")
        print(f"   Tasks: {len(suite.tasks)}")
        
        # Sort by priority
        sorted_tasks = sorted(suite.tasks, key=lambda t: t.priority)
        
        if parallel:
            # Run tasks in parallel
            print(f"   Mode: Parallel")
            results = await asyncio.gather(
                *[self.run_task(task) for task in sorted_tasks],
                return_exceptions=True
            )
        else:
            # Run tasks sequentially
            print(f"   Mode: Sequential")
            for task in sorted_tasks:
                await self.run_task(task)
        
        # Save suite results
        self._save_suite_results(suite)
        
        # Print summary
        self._print_suite_summary(suite)
        
        return suite
    
    async def run_all_suites(self, parallel: bool = False):
        """Execute all benchmark suites"""
        
        print(f"\n🌟 Running All Benchmark Suites")
        print("=" * 60)
        
        for suite_id in self.suites:
            await self.run_suite(suite_id, parallel=parallel)
        
        print(f"\n\n🎉 All Suites Complete!")
        self._print_overall_summary()
    
    def _save_suite_results(self, suite: BenchmarkSuite):
        """Save suite results to file"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.results_dir / f"suite_{suite.suite_id}_{timestamp}.json"
        
        output = {
            "suite_id": suite.suite_id,
            "name": suite.name,
            "description": suite.description,
            "created_at": suite.created_at,
            "completed_at": datetime.now().isoformat(),
            "tasks": [asdict(task) for task in suite.tasks]
        }
        
        with open(filename, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Suite results saved: {filename}")
    
    def _print_suite_summary(self, suite: BenchmarkSuite):
        """Print suite execution summary"""
        
        print(f"\n📊 Suite Summary: {suite.name}")
        print("=" * 60)
        
        total = len(suite.tasks)
        completed = sum(1 for t in suite.tasks if t.status == "completed")
        failed = sum(1 for t in suite.tasks if t.status == "failed")
        
        print(f"Total Tasks: {total}")
        print(f"Completed: {completed}")
        print(f"Failed: {failed}")
        
        if completed > 0:
            print(f"\n✅ Completed Tasks:")
            for task in suite.tasks:
                if task.status == "completed":
                    print(f"   - {task.name}")
        
        if failed > 0:
            print(f"\n❌ Failed Tasks:")
            for task in suite.tasks:
                if task.status == "failed":
                    print(f"   - {task.name}: {task.error}")
    
    def _print_overall_summary(self):
        """Print overall execution summary"""
        
        print(f"\n📊 Overall Summary")
        print("=" * 60)
        
        total_tasks = len(self.tasks)
        total_completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        total_failed = sum(1 for t in self.tasks.values() if t.status == "failed")
        
        print(f"Total Suites: {len(self.suites)}")
        print(f"Total Tasks: {total_tasks}")
        print(f"Completed: {total_completed} ({total_completed/total_tasks*100:.1f}%)")
        print(f"Failed: {total_failed} ({total_failed/total_tasks*100:.1f}%)")
        
        print(f"\n📁 Results Directory: {self.results_dir}")
        print(f"📁 Logs Directory: {self.logs_dir}")
    
    def get_task_status(self, task_id: str) -> Optional[BenchmarkTask]:
        """Get status of a specific task"""
        return self.tasks.get(task_id)
    
    def get_suite_status(self, suite_id: str) -> Optional[BenchmarkSuite]:
        """Get status of a specific suite"""
        return self.suites.get(suite_id)
    
    def export_results(self, output_file: str = "benchmark_results_summary.json"):
        """Export all results to a single file"""
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_suites": len(self.suites),
            "total_tasks": len(self.tasks),
            "suites": {}
        }
        
        for suite_id, suite in self.suites.items():
            summary["suites"][suite_id] = {
                "name": suite.name,
                "description": suite.description,
                "created_at": suite.created_at,
                "tasks": [asdict(task) for task in suite.tasks]
            }
        
        output_path = self.results_dir / output_file
        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"📊 Results exported: {output_path}")
        return output_path

async def main():
    """Example orchestrator usage"""
    
    print("🔬 S2 Intelligence Benchmark Orchestrator")
    print("=" * 60)
    
    # Initialize
    try:
        from together_integration import TogetherClient, TogetherConfig
        
        config = TogetherConfig(api_key=os.getenv("TOGETHER_API_KEY"))
        client = TogetherClient(config)
        orchestrator = BenchmarkOrchestrator(client)
        
        # Create default suites
        orchestrator.create_default_suites()
        
        # Option 1: Run specific suite
        print("\n1️⃣ Run specific suite:")
        print("   await orchestrator.run_suite('standard_llm')")
        
        # Option 2: Run all suites
        print("\n2️⃣ Run all suites:")
        print("   await orchestrator.run_all_suites()")
        
        # Option 3: Run with config file
        print("\n3️⃣ Run with config file:")
        print("   orchestrator.load_config('benchmark_config.json')")
        print("   await orchestrator.run_all_suites()")
        
        # Export results
        print("\n4️⃣ Export results:")
        print("   orchestrator.export_results()")
        
        print("\n✅ Orchestrator ready!")
        print("\n💡 To actually run benchmarks:")
        print("   python orchestrator.py --run-all")
        
    except Exception as e:
        print(f"❌ Initialization failed: {e}")

if __name__ == "__main__":
    import sys
    
    if "--run-all" in sys.argv:
        # Actually run benchmarks
        async def run_all():
            config = TogetherConfig(api_key=os.getenv("TOGETHER_API_KEY"))
            client = TogetherClient(config)
            orchestrator = BenchmarkOrchestrator(client)
            orchestrator.create_default_suites()
            await orchestrator.run_all_suites()
            orchestrator.export_results()
        
        asyncio.run(run_all())
    else:
        # Just show information
        asyncio.run(main())
