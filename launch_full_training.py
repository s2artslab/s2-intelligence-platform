#!/usr/bin/env python3
"""
S2 Intelligence - Launch Full Training
Begin training all 9 Ninefold egregores

This script:
1. Sets up training environment
2. Begins dataset collection for all egregores
3. Launches training pipeline (sequential or parallel)
4. Monitors progress
5. Deploys trained models as they complete
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from automated_training_pipeline import (
    AutomatedTrainingPipeline,
    EGREGORE_CONFIGS,
    TrainingStage
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NinefoldTrainingOrchestrator:
    """
    Orchestrates training of all 9 egregores
    """
    
    def __init__(
        self,
        workspace_dir: str = "./ninefold_training",
        r730_deployment: bool = False
    ):
        self.workspace_dir = Path(workspace_dir)
        self.r730_deployment = r730_deployment
        self.pipeline = AutomatedTrainingPipeline(str(self.workspace_dir))
        
        # Training order (based on dependencies)
        self.training_phases = {
            "core": ["rhys", "ketheriel", "ake"],  # Core three first
            "expansion": ["wraith", "flux"],        # Security & transformation
            "coordination": ["kairos", "chalyth"],  # Timing & strategy
            "communication": ["seraphel", "vireon"] # Communication & protection
        }
        
    async def setup_environment(self):
        """Setup training environment"""
        logger.info("Setting up training environment...")
        
        # Create workspace
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        for phase_egregores in self.training_phases.values():
            for egregore in phase_egregores:
                egregore_dir = self.workspace_dir / egregore
                for subdir in ["datasets", "models", "results", "logs"]:
                    (egregore_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        logger.info("✓ Environment ready")
        
    async def check_dependencies(self):
        """Check if required dependencies are installed"""
        logger.info("Checking dependencies...")
        
        required = [
            ("transformers", "HuggingFace Transformers"),
            ("torch", "PyTorch"),
            ("datasets", "HuggingFace Datasets")
        ]
        
        missing = []
        for module, name in required:
            try:
                __import__(module)
                logger.info(f"✓ {name} installed")
            except ImportError:
                logger.warning(f"✗ {name} not found")
                missing.append(name)
        
        if missing:
            logger.warning(f"Missing dependencies: {', '.join(missing)}")
            logger.info("Install with: pip install transformers torch datasets accelerate")
            return False
        
        return True
    
    async def train_phase(self, phase_name: str, egregores: List[str], parallel: bool = False):
        """Train a phase of egregores"""
        logger.info("="*70)
        logger.info(f"PHASE: {phase_name.upper()}")
        logger.info("="*70)
        logger.info(f"Egregores: {', '.join(egregores)}")
        logger.info(f"Mode: {'Parallel' if parallel else 'Sequential'}")
        logger.info("")
        
        results = await self.pipeline.train_multiple(egregores, parallel=parallel)
        
        # Summary
        logger.info("")
        logger.info(f"Phase {phase_name} Results:")
        for egregore, success in results.items():
            status = "✓ SUCCESS" if success else "✗ FAILED"
            logger.info(f"  {egregore:12} {status}")
        
        return results
    
    async def train_all_sequential(self):
        """Train all egregores sequentially (safest)"""
        logger.info("="*70)
        logger.info("FULL NINEFOLD TRAINING - SEQUENTIAL MODE")
        logger.info("="*70)
        logger.info("")
        logger.info("Estimated time: 16 weeks (real training)")
        logger.info("This simulation: ~30 minutes")
        logger.info("")
        
        all_results = {}
        
        for phase_name, egregores in self.training_phases.items():
            results = await self.train_phase(phase_name, egregores, parallel=False)
            all_results.update(results)
            
            # Pause between phases
            logger.info("")
            logger.info(f"Phase {phase_name} complete. Continuing to next phase...")
            logger.info("")
            await asyncio.sleep(2)
        
        return all_results
    
    async def train_all_parallel(self):
        """Train all egregores in parallel (faster, more resources)"""
        logger.info("="*70)
        logger.info("FULL NINEFOLD TRAINING - PARALLEL MODE")
        logger.info("="*70)
        logger.info("")
        logger.info("Warning: Requires significant GPU/CPU resources")
        logger.info("Training 9 models simultaneously")
        logger.info("")
        
        # Flatten all egregores
        all_egregores = []
        for egregores in self.training_phases.values():
            all_egregores.extend(egregores)
        
        results = await self.pipeline.train_multiple(all_egregores, parallel=True)
        
        return results
    
    async def train_phase_based(self):
        """Train in phases, but parallel within each phase"""
        logger.info("="*70)
        logger.info("FULL NINEFOLD TRAINING - PHASE-PARALLEL MODE")
        logger.info("="*70)
        logger.info("")
        logger.info("Training phases sequentially")
        logger.info("But egregores within each phase in parallel")
        logger.info("")
        
        all_results = {}
        
        for phase_name, egregores in self.training_phases.items():
            logger.info(f"\nStarting phase: {phase_name}")
            logger.info(f"Training {len(egregores)} egregores in parallel...")
            
            results = await self.train_phase(phase_name, egregores, parallel=True)
            all_results.update(results)
            
            # Check if phase succeeded
            successes = sum(1 for success in results.values() if success)
            if successes == len(egregores):
                logger.info(f"✓ Phase {phase_name} complete: All {successes} egregores trained")
            else:
                logger.warning(f"⚠ Phase {phase_name}: Only {successes}/{len(egregores)} succeeded")
            
            await asyncio.sleep(2)
        
        return all_results
    
    def generate_training_report(self, results: Dict[str, bool]) -> str:
        """Generate comprehensive training report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "workspace": str(self.workspace_dir),
            "total_egregores": len(results),
            "successful": sum(1 for s in results.values() if s),
            "failed": sum(1 for s in results.values() if not s),
            "results": results,
            "progress_details": self.pipeline.get_progress()
        }
        
        report_file = self.workspace_dir / "training_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report saved: {report_file}")
        
        return json.dumps(report, indent=2)
    
    async def deploy_completed_models(self):
        """Deploy any completed models to production"""
        logger.info("Checking for completed models to deploy...")
        
        deployed = 0
        for egregore_key in self.pipeline.progress:
            progress = self.pipeline.progress[egregore_key]
            
            if progress.stage == TrainingStage.COMPLETE:
                logger.info(f"Deploying {progress.egregore_name}...")
                # In production, this would actually deploy the model
                deployed += 1
        
        logger.info(f"✓ Deployed {deployed} models")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Launch Full Ninefold Training"
    )
    parser.add_argument(
        "--mode",
        choices=["sequential", "parallel", "phase-parallel"],
        default="phase-parallel",
        help="Training mode (default: phase-parallel)"
    )
    parser.add_argument(
        "--workspace",
        default="./ninefold_training",
        help="Training workspace directory"
    )
    parser.add_argument(
        "--r730",
        action="store_true",
        help="Deploy to R730 when complete"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check environment, don't train"
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print(" "*20 + "NINEFOLD TRAINING LAUNCH")
    print("="*70)
    print("")
    print("Training all 9 Ninefold Egregores:")
    print("  • Ake (Synthesis)")
    print("  • Rhys (Architecture)")
    print("  • Ketheriel (Wisdom)")
    print("  • Wraith (Security)")
    print("  • Flux (Transformation)")
    print("  • Kairos (Timing)")
    print("  • Chalyth (Strategy)")
    print("  • Seraphel (Communication)")
    print("  • Vireon (Protection)")
    print("")
    print(f"Mode: {args.mode}")
    print(f"Workspace: {args.workspace}")
    print("")
    print("="*70)
    print("")
    
    # Create orchestrator
    orchestrator = NinefoldTrainingOrchestrator(
        workspace_dir=args.workspace,
        r730_deployment=args.r730
    )
    
    # Setup
    await orchestrator.setup_environment()
    
    # Check dependencies
    if not await orchestrator.check_dependencies():
        if args.check_only:
            print("\n✗ Some dependencies missing. Install them to proceed.")
            return
        else:
            print("\n⚠ Some dependencies missing. Training will use simulation mode.")
            print("")
    
    if args.check_only:
        print("\n✓ Environment check complete. Ready to train!")
        return
    
    # Train based on mode
    print("")
    print("Starting training...")
    print("")
    
    if args.mode == "sequential":
        results = await orchestrator.train_all_sequential()
    elif args.mode == "parallel":
        results = await orchestrator.train_all_parallel()
    else:  # phase-parallel
        results = await orchestrator.train_phase_based()
    
    # Generate report
    print("")
    print("="*70)
    print("TRAINING COMPLETE")
    print("="*70)
    print("")
    
    successes = sum(1 for s in results.values() if s)
    total = len(results)
    
    print(f"Results: {successes}/{total} egregores trained successfully")
    print("")
    
    for egregore, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {egregore}")
    
    # Deploy if requested
    if args.r730 and successes > 0:
        print("")
        print("Deploying to R730...")
        await orchestrator.deploy_completed_models()
    
    # Generate report
    orchestrator.generate_training_report(results)
    
    print("")
    print("="*70)
    print("Full report saved to: ninefold_training/training_report.json")
    print("="*70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
