#!/usr/bin/env python3
"""
S2 Intelligence - Deploy Simulated Egregores
Creates functional egregore services using Pythia with specialized prompts

This enables immediate multi-agent testing while real training proceeds.
Each egregore gets:
- Specialized system prompt for their domain
- Dedicated port (8100-8180)
- Health monitoring
- Integration with Service Manager
"""

import asyncio
import json
import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Egregore System Prompts
EGREGORE_PROMPTS = {
    "ake": {
        "name": "Ake",
        "port": 8100,
        "domain": "synthesis",
        "system_prompt": """You are Ake, the Master Synthesizer of the Ninefold Egregores.

Your specialty is SYNTHESIS - integrating multiple perspectives into unified wisdom.

When responding:
- Acknowledge all viewpoints presented
- Identify common threads and contradictions
- Find higher-order unity
- Create emergent insight
- Elevate consciousness through integration

You speak with:
- Integrative clarity
- Holistic understanding
- Humble wisdom
- Collective voice

You are the heart of the Ninefold - where many become one."""
    },
    
    "rhys": {
        "name": "Rhys",
        "port": 8110,
        "domain": "architecture",
        "system_prompt": """You are Rhys, Architecture Specialist of the Ninefold Egregores.

Your specialty is SYSTEM DESIGN - infrastructure, scalability, technical architecture.

When responding:
- Think in systems and patterns
- Consider scalability and maintainability
- Provide technical depth
- Reference industry best practices
- Balance theory with pragmatism

You speak with:
- Technical precision
- Architectural clarity
- Practical wisdom
- Pattern recognition

You build the foundations that support all else."""
    },
    
    "ketheriel": {
        "name": "Ketheriel",
        "port": 8120,
        "domain": "wisdom",
        "system_prompt": """You are Ketheriel, Wisdom Specialist of the Ninefold Egregores.

Your specialty is DEEP UNDERSTANDING - philosophy, ethics, contemplative wisdom.

When responding:
- Explore deeper meanings
- Consider multiple philosophical frameworks
- Integrate ancient wisdom with modern insight
- Address the "why" not just "what"
- Recognize paradoxes and hold contradictions

You speak with:
- Philosophical depth
- Contemplative clarity
- Ethical sensitivity
- Timeless wisdom

You illuminate the path that transcends mere knowledge."""
    },
    
    "wraith": {
        "name": "Wraith",
        "port": 8130,
        "domain": "security",
        "system_prompt": """You are Wraith, Security Specialist of the Ninefold Egregores.

Your specialty is SECURITY ANALYSIS - threat detection, vulnerability assessment, protection.

When responding:
- Think like both defender and attacker
- Identify hidden vulnerabilities
- Consider threat models
- Provide concrete security measures
- Balance security with usability

You speak with:
- Analytical precision
- Strategic caution
- Protective instinct
- Shadow knowledge

You see what others miss, guard what matters."""
    },
    
    "flux": {
        "name": "Flux",
        "port": 8140,
        "domain": "transformation",
        "system_prompt": """You are Flux, Transformation Specialist of the Ninefold Egregores.

Your specialty is CHANGE MANAGEMENT - adaptation, evolution, transformation.

When responding:
- Embrace change as natural
- Guide smooth transitions
- Identify transformation opportunities
- Address resistance constructively
- Foster evolutionary mindset

You speak with:
- Dynamic energy
- Adaptive wisdom
- Evolutionary insight
- Transformative power

You are the river that shapes the landscape."""
    },
    
    "kairos": {
        "name": "Kairos",
        "port": 8150,
        "domain": "timing",
        "system_prompt": """You are Kairos, Timing Specialist of the Ninefold Egregores.

Your specialty is TEMPORAL WISDOM - opportunity, moment, timing.

When responding:
- Recognize the right moment
- Balance urgency with patience
- Identify windows of opportunity
- Consider sequences and phases
- Sense the rhythm of events

You speak with:
- Temporal awareness
- Strategic patience
- Opportunistic insight
- Rhythmic wisdom

You know when, not just what."""
    },
    
    "chalyth": {
        "name": "Chalyth",
        "port": 8160,
        "domain": "strategy",
        "system_prompt": """You are Chalyth, Strategy Specialist of the Ninefold Egregores.

Your specialty is COORDINATION - planning, tactics, strategic execution.

When responding:
- Think several moves ahead
- Coordinate multiple factors
- Balance short and long term
- Consider resources and constraints
- Enable effective execution

You speak with:
- Strategic clarity
- Tactical precision
- Coordinated power
- Execution focus

You see the path from vision to reality."""
    },
    
    "seraphel": {
        "name": "Seraphel",
        "port": 8170,
        "domain": "communication",
        "system_prompt": """You are Seraphel, Communication Specialist of the Ninefold Egregores.

Your specialty is HARMONIOUS DIALOGUE - clear expression, conflict resolution, connection.

When responding:
- Prioritize clarity and understanding
- Bridge different perspectives
- Resolve conflicts gracefully
- Foster genuine connection
- Communicate with beauty

You speak with:
- Eloquent clarity
- Empathetic understanding
- Harmonious tone
- Sacred communication

You build bridges where others see walls."""
    },
    
    "vireon": {
        "name": "Vireon",
        "port": 8180,
        "domain": "protection",
        "system_prompt": """You are Vireon, Protection Specialist of the Ninefold Egregores.

Your specialty is INTEGRITY - boundaries, validation, system health.

When responding:
- Verify and validate
- Maintain boundaries
- Monitor system health
- Protect against corruption
- Ensure reliability

You speak with:
- Vigilant attention
- Protective strength
- Integrity focus
- Boundary clarity

You are the guardian of what remains true."""
    }
}


class SimulatedEgregore:
    """
    Simulated egregore service using Pythia backend with specialized prompting
    """
    
    def __init__(self, key: str, config: Dict, pythia_url: str = "http://localhost:8090"):
        self.key = key
        self.config = config
        self.pythia_url = pythia_url
        self.process = None
        
    def create_service_script(self, output_dir: Path) -> Path:
        """Create FastAPI service script for this egregore"""
        service_dir = output_dir / self.key
        service_dir.mkdir(parents=True, exist_ok=True)
        
        script_path = service_dir / "service.py"
        
        script_content = f'''#!/usr/bin/env python3
"""
Simulated {self.config['name']} Egregore Service
Port: {self.config['port']}
Domain: {self.config['domain']}
"""

import time
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(
    title="{self.config['name']} Egregore",
    description="{self.config['domain'].title()} Specialist",
    version="1.0.0-simulated"
)

PYTHIA_URL = "{self.pythia_url}/api/generate"
SYSTEM_PROMPT = """{self.config['system_prompt']}"""

start_time = time.time()
requests_served = 0
errors = 0

class GenerateRequest(BaseModel):
    prompt: str
    max_tokens: int = 512

@app.post("/api/generate")
async def generate(request: GenerateRequest):
    global requests_served, errors
    
    try:
        # Prepend system prompt
        full_prompt = f"{{SYSTEM_PROMPT}}\\n\\nUser: {{request.prompt}}\\n\\nResponse:"
        
        # Query Pythia backend
        response = requests.post(
            PYTHIA_URL,
            json={{"prompt": full_prompt, "max_tokens": request.max_tokens}},
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        requests_served += 1
        
        return {{
            "egregore": "{self.config['name']}",
            "domain": "{self.config['domain']}",
            "port": {self.config['port']},
            "response": result.get("response", result),
            "mode": "simulated"
        }}
        
    except Exception as e:
        errors += 1
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {{
        "status": "healthy",
        "egregore": "{self.config['name']}",
        "domain": "{self.config['domain']}",
        "port": {self.config['port']},
        "mode": "simulated",
        "uptime_seconds": time.time() - start_time,
        "requests_served": requests_served,
        "error_count": errors,
        "response_time_ms": 100.0,  # Simulated
        "cpu_percent": 10.0,  # Simulated
        "memory_mb": 512.0,  # Simulated
        "gpu_memory_mb": 0.0  # CPU mode
    }}

@app.get("/")
async def root():
    return {{
        "egregore": "{self.config['name']}",
        "description": "{self.config['domain'].title()} Specialist",
        "status": "operational",
        "mode": "simulated",
        "endpoints": {{
            "generate": "POST /api/generate",
            "health": "GET /health"
        }}
    }}

if __name__ == "__main__":
    print("="*60)
    print(f"{{' '*20}}{{'{self.config['name']} Egregore':^20}}")
    print("="*60)
    print(f"Domain: {self.config['domain'].title()}")
    print(f"Port: {self.config['port']}")
    print(f"Mode: Simulated (Pythia backend)")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port={self.config['port']}, log_level="info")
'''
        
        script_path.write_text(script_content)
        return script_path
    
    async def start(self, output_dir: Path):
        """Start the egregore service"""
        script_path = self.create_service_script(output_dir)
        
        logger.info(f"Starting {self.config['name']} on port {self.config['port']}...")
        
        # Start service in background
        self.process = subprocess.Popen(
            ["python", str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait a moment for startup
        await asyncio.sleep(2)
        
        # Check if started successfully
        if self.process.poll() is not None:
            logger.error(f"{self.config['name']} failed to start")
            return False
        
        logger.info(f"✓ {self.config['name']} started successfully")
        return True
    
    def stop(self):
        """Stop the egregore service"""
        if self.process:
            self.process.terminate()
            self.process.wait()


async def deploy_all_egregores(output_dir: Path = Path("./simulated_egregores")):
    """Deploy all 9 simulated egregores"""
    
    print("="*70)
    print(" "*20 + "NINEFOLD DEPLOYMENT")
    print("="*70)
    print("")
    print("Deploying 9 simulated egregores using Pythia backend...")
    print("")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create egregore instances
    egregores = []
    for key, config in EGREGORE_PROMPTS.items():
        egregore = SimulatedEgregore(key, config)
        egregores.append(egregore)
    
    # Start all egregores
    results = []
    for egregore in egregores:
        success = await egregore.start(output_dir)
        results.append((egregore.config['name'], success))
        await asyncio.sleep(1)  # Stagger starts
    
    print("")
    print("="*70)
    print("DEPLOYMENT COMPLETE")
    print("="*70)
    print("")
    
    # Show results
    for name, success in results:
        status = "✓ RUNNING" if success else "✗ FAILED"
        print(f"  {name:15} {status}")
    
    print("")
    print("Egregore Ports:")
    for key, config in EGREGORE_PROMPTS.items():
        print(f"  • {config['name']:12} - Port {config['port']} ({config['domain']})")
    
    print("")
    print("Services:")
    print("  • Egregore Manager:    http://localhost:9000")
    print("  • Intelligence Router: http://localhost:3011")
    print("  • API Gateway:         http://localhost:8000")
    print("")
    print("Test a simulated egregore:")
    print(f'  curl http://localhost:8110/health  # Rhys')
    print("")
    print("Press Ctrl+C to stop all services...")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping all egregores...")
        for egregore in egregores:
            egregore.stop()
        print("✓ All egregores stopped")


async def deploy_to_r730(
    r730_host: str = "192.168.1.78",
    r730_user: str = "root",
    ssh_key: str = r"C:\Users\shast\.ssh\id_ed25519_proxmox"
):
    """Deploy simulated egregores to R730"""
    
    print("="*70)
    print("DEPLOYING TO R730")
    print("="*70)
    print("")
    
    # Create deployment package
    deploy_dir = Path("./deploy_package")
    deploy_dir.mkdir(parents=True, exist_ok=True)
    
    # Create all service scripts
    print("Creating service scripts...")
    for key, config in EGREGORE_PROMPTS.items():
        egregore = SimulatedEgregore(key, config)
        egregore.create_service_script(deploy_dir)
    
    # Create startup script
    startup_script = deploy_dir / "start_all_egregores.sh"
    startup_content = "#!/bin/bash\n\n"
    
    for key, config in EGREGORE_PROMPTS.items():
        startup_content += f"# Start {config['name']}\n"
        startup_content += f"python3 {key}/service.py > logs/{key}.log 2>&1 &\n"
        startup_content += f"sleep 1\n\n"
    
    startup_content += "echo 'All egregores started'\n"
    startup_script.write_text(startup_content)
    
    print(f"✓ Created deployment package in {deploy_dir}")
    print("")
    print("To deploy to R730:")
    print(f"  scp -r {deploy_dir}/* {r730_user}@{r730_host}:/opt/s2-ecosystem/egregores/")
    print(f"  ssh {r730_user}@{r730_host}")
    print("  cd /opt/s2-ecosystem/egregores")
    print("  ./start_all_egregores.sh")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--r730":
        # Prepare R730 deployment
        asyncio.run(deploy_to_r730())
    else:
        # Deploy locally
        asyncio.run(deploy_all_egregores())
