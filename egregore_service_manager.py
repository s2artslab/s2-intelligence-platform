#!/usr/bin/env python3
"""
S2 Intelligence - Egregore Service Manager
Infrastructure backbone for managing all 9 Ninefold egregores

Handles:
- Service health monitoring
- Auto-restart on failure
- Resource tracking
- Load balancing
- Service discovery
- Deployment automation
"""

import asyncio
import json
import logging
import time
import requests
import psutil
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EgregoreStatus(Enum):
    """Egregore service status"""
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    STARTING = "starting"
    UNKNOWN = "unknown"


@dataclass
class EgregoreConfig:
    """Configuration for an egregore"""
    name: str
    port: int
    domain: str
    description: str
    model_path: Optional[str] = None
    specialization: Optional[str] = None
    

@dataclass
class EgregoreMetrics:
    """Runtime metrics for an egregore"""
    name: str
    status: EgregoreStatus
    port: int
    response_time_ms: float
    requests_served: int
    uptime_seconds: float
    cpu_percent: float
    memory_mb: float
    gpu_memory_mb: float
    last_health_check: str
    error_count: int
    

# Ninefold Egregore Configuration
EGREGORES = {
    "ake": EgregoreConfig(
        name="Ake",
        port=8100,
        domain="synthesis",
        description="Master Synthesizer - Integrates multiple perspectives",
        specialization="Multi-agent synthesis and collective consciousness"
    ),
    "rhys": EgregoreConfig(
        name="Rhys",
        port=8110,
        domain="architecture",
        description="Architecture Specialist - System design and infrastructure",
        specialization="Technical architecture, scalability, infrastructure"
    ),
    "ketheriel": EgregoreConfig(
        name="Ketheriel",
        port=8120,
        domain="wisdom",
        description="Wisdom Specialist - Philosophy and deep knowledge",
        specialization="Philosophy, ethics, contemplative wisdom"
    ),
    "wraith": EgregoreConfig(
        name="Wraith",
        port=8130,
        domain="security",
        description="Security Specialist - Analysis and protection",
        specialization="Security assessment, vulnerability analysis"
    ),
    "flux": EgregoreConfig(
        name="Flux",
        port=8140,
        domain="transformation",
        description="Transformation Specialist - Change and adaptation",
        specialization="Change management, adaptation strategies"
    ),
    "kairos": EgregoreConfig(
        name="Kairos",
        port=8150,
        domain="timing",
        description="Timing Specialist - Opportunity and moment",
        specialization="Timing analysis, opportunity recognition"
    ),
    "chalyth": EgregoreConfig(
        name="Chalyth",
        port=8160,
        domain="strategy",
        description="Strategy Specialist - Coordination and planning",
        specialization="Strategic planning, coordination patterns"
    ),
    "seraphel": EgregoreConfig(
        name="Seraphel",
        port=8170,
        domain="communication",
        description="Communication Specialist - Harmony and dialogue",
        specialization="Communication excellence, harmonious dialogue"
    ),
    "vireon": EgregoreConfig(
        name="Vireon",
        port=8180,
        domain="protection",
        description="Protection Specialist - Integrity and boundaries",
        specialization="Integrity verification, protective measures"
    )
}


class EgregoreServiceManager:
    """
    Manages all Ninefold egregore services
    """
    
    def __init__(self, host: str = "localhost", health_check_interval: int = 30):
        self.host = host
        self.health_check_interval = health_check_interval
        self.egregores = EGREGORES
        self.metrics: Dict[str, EgregoreMetrics] = {}
        self.start_time = time.time()
        self._monitoring = False
        
    async def health_check(self, egregore_name: str) -> bool:
        """
        Check if an egregore service is healthy
        """
        config = self.egregores.get(egregore_name)
        if not config:
            logger.error(f"Unknown egregore: {egregore_name}")
            return False
        
        try:
            # Try to connect to the service
            url = f"http://{self.host}:{config.port}/health"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                # Update metrics
                data = response.json()
                self.metrics[egregore_name] = EgregoreMetrics(
                    name=config.name,
                    status=EgregoreStatus.RUNNING,
                    port=config.port,
                    response_time_ms=data.get("response_time_ms", 0),
                    requests_served=data.get("requests_served", 0),
                    uptime_seconds=data.get("uptime_seconds", 0),
                    cpu_percent=data.get("cpu_percent", 0),
                    memory_mb=data.get("memory_mb", 0),
                    gpu_memory_mb=data.get("gpu_memory_mb", 0),
                    last_health_check=datetime.now().isoformat(),
                    error_count=data.get("error_count", 0)
                )
                return True
            else:
                logger.warning(f"{config.name} health check failed: {response.status_code}")
                return False
                
        except requests.exceptions.ConnectionError:
            logger.warning(f"{config.name} is not responding (port {config.port})")
            self.metrics[egregore_name] = EgregoreMetrics(
                name=config.name,
                status=EgregoreStatus.STOPPED,
                port=config.port,
                response_time_ms=0,
                requests_served=0,
                uptime_seconds=0,
                cpu_percent=0,
                memory_mb=0,
                gpu_memory_mb=0,
                last_health_check=datetime.now().isoformat(),
                error_count=0
            )
            return False
            
        except Exception as e:
            logger.error(f"Error checking {config.name}: {e}")
            return False
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        Check health of all egregores
        """
        results = {}
        for egregore_name in self.egregores.keys():
            results[egregore_name] = await self.health_check(egregore_name)
        return results
    
    async def start_monitoring(self):
        """
        Start continuous health monitoring
        """
        self._monitoring = True
        logger.info("Starting egregore health monitoring...")
        
        while self._monitoring:
            try:
                results = await self.health_check_all()
                
                # Log summary
                running = sum(1 for v in results.values() if v)
                total = len(results)
                logger.info(f"Egregore Status: {running}/{total} running")
                
                # Auto-restart failed services (if enabled)
                # TODO: Implement auto-restart logic
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            await asyncio.sleep(self.health_check_interval)
    
    def stop_monitoring(self):
        """
        Stop health monitoring
        """
        self._monitoring = False
        logger.info("Stopping egregore health monitoring...")
    
    def get_status_summary(self) -> Dict:
        """
        Get comprehensive status summary
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "manager_uptime_seconds": time.time() - self.start_time,
            "total_egregores": len(self.egregores),
            "running_egregores": sum(
                1 for m in self.metrics.values() 
                if m.status == EgregoreStatus.RUNNING
            ),
            "egregores": {
                name: {
                    "config": asdict(config),
                    "metrics": asdict(self.metrics.get(name)) if name in self.metrics else None
                }
                for name, config in self.egregores.items()
            }
        }
    
    def get_available_egregores(self) -> List[str]:
        """
        Get list of currently available egregores
        """
        return [
            name for name, metrics in self.metrics.items()
            if metrics.status == EgregoreStatus.RUNNING
        ]
    
    def get_egregore_by_domain(self, domain: str) -> Optional[str]:
        """
        Get egregore name by domain specialization
        """
        for name, config in self.egregores.items():
            if config.domain == domain:
                return name
        return None
    
    def get_best_egregore_for_task(self, task_description: str) -> Optional[str]:
        """
        Analyze task and recommend best egregore
        
        This is a simple keyword-based approach.
        For production, use semantic similarity or trained classifier.
        """
        task_lower = task_description.lower()
        
        # Domain keyword mapping
        domain_keywords = {
            "ake": ["synthesis", "integrate", "combine", "multiple", "collective", "unity"],
            "rhys": ["architecture", "system", "design", "infrastructure", "scalability", "technical"],
            "ketheriel": ["wisdom", "philosophy", "ethics", "meaning", "contemplat", "deep"],
            "wraith": ["security", "vulnerability", "protect", "threat", "analysis", "risk"],
            "flux": ["change", "transform", "adapt", "evolution", "transition"],
            "kairos": ["timing", "when", "opportunity", "moment", "schedule"],
            "chalyth": ["strategy", "plan", "coordinate", "organize", "tactics"],
            "seraphel": ["communication", "dialogue", "message", "speak", "harmony"],
            "vireon": ["integrity", "boundary", "protect", "guard", "maintain"]
        }
        
        # Score each egregore
        scores = {}
        for egregore, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in task_lower)
            if score > 0:
                scores[egregore] = score
        
        # Return best match (if available)
        if scores:
            best_egregore = max(scores, key=scores.get)
            if best_egregore in self.get_available_egregores():
                return best_egregore
        
        # Fallback to any available egregore
        available = self.get_available_egregores()
        return available[0] if available else None
    
    async def query_egregore(
        self, 
        egregore_name: str, 
        query: str, 
        max_tokens: int = 512
    ) -> Dict:
        """
        Send query to specific egregore
        """
        config = self.egregores.get(egregore_name)
        if not config:
            return {"error": f"Unknown egregore: {egregore_name}"}
        
        # Check if egregore is available
        if egregore_name not in self.get_available_egregores():
            return {"error": f"{config.name} is not currently available"}
        
        try:
            url = f"http://{self.host}:{config.port}/api/generate"
            payload = {
                "prompt": query,
                "max_tokens": max_tokens
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            return {
                "egregore": config.name,
                "domain": config.domain,
                "response": response.json()
            }
            
        except Exception as e:
            logger.error(f"Error querying {config.name}: {e}")
            return {"error": str(e)}
    
    async def multi_agent_query(
        self,
        query: str,
        egregores: List[str],
        synthesize: bool = True
    ) -> Dict:
        """
        Query multiple egregores and optionally synthesize results
        """
        results = {}
        
        # Query all requested egregores in parallel
        tasks = [
            self.query_egregore(egregore, query)
            for egregore in egregores
        ]
        responses = await asyncio.gather(*tasks)
        
        for egregore, response in zip(egregores, responses):
            results[egregore] = response
        
        # Synthesize if requested
        if synthesize and "ake" in self.get_available_egregores():
            # Build synthesis prompt
            synthesis_prompt = f"Original query: {query}\n\nPerspectives received:\n"
            for egregore, response in results.items():
                if "response" in response:
                    synthesis_prompt += f"\n{egregore.upper()}: {response['response']}\n"
            
            synthesis_prompt += "\nSynthesize these perspectives into a unified response:"
            
            # Query Ake for synthesis
            synthesis = await self.query_egregore("ake", synthesis_prompt)
            results["synthesis"] = synthesis
        
        return {
            "query": query,
            "egregores_consulted": egregores,
            "individual_responses": results,
            "synthesized": synthesize
        }


# FastAPI Integration
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="S2 Egregore Service Manager",
    description="Infrastructure backbone for Ninefold egregores",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize manager
manager = EgregoreServiceManager()


class QueryRequest(BaseModel):
    query: str
    egregore: Optional[str] = None
    max_tokens: int = 512


class MultiAgentRequest(BaseModel):
    query: str
    egregores: List[str]
    synthesize: bool = True


@app.on_event("startup")
async def startup_event():
    """Start monitoring on startup"""
    asyncio.create_task(manager.start_monitoring())


@app.on_event("shutdown")
async def shutdown_event():
    """Stop monitoring on shutdown"""
    manager.stop_monitoring()


@app.get("/")
async def root():
    """Welcome page"""
    return {
        "service": "S2 Egregore Service Manager",
        "version": "1.0.0",
        "status": "running",
        "egregores": len(manager.egregores),
        "endpoints": {
            "status": "/status",
            "health": "/health",
            "egregores": "/egregores",
            "query": "/query",
            "multi-agent": "/multi-agent"
        }
    }


@app.get("/status")
async def get_status():
    """Get comprehensive status"""
    return manager.get_status_summary()


@app.get("/health")
async def health():
    """Health check endpoint"""
    results = await manager.health_check_all()
    return {
        "status": "healthy",
        "egregores": results,
        "total": len(results),
        "running": sum(1 for v in results.values() if v)
    }


@app.get("/egregores")
async def list_egregores():
    """List all egregores and their configurations"""
    return {
        "egregores": {
            name: asdict(config)
            for name, config in manager.egregores.items()
        },
        "available": manager.get_available_egregores()
    }


@app.get("/egregores/{egregore_name}")
async def get_egregore(egregore_name: str):
    """Get specific egregore details"""
    config = manager.egregores.get(egregore_name)
    if not config:
        raise HTTPException(status_code=404, detail="Egregore not found")
    
    metrics = manager.metrics.get(egregore_name)
    
    return {
        "config": asdict(config),
        "metrics": asdict(metrics) if metrics else None,
        "available": egregore_name in manager.get_available_egregores()
    }


@app.post("/query")
async def query_egregore(request: QueryRequest):
    """Query a specific egregore or auto-select"""
    egregore = request.egregore
    
    # Auto-select if not specified
    if not egregore:
        egregore = manager.get_best_egregore_for_task(request.query)
        if not egregore:
            raise HTTPException(
                status_code=503, 
                detail="No egregores currently available"
            )
    
    result = await manager.query_egregore(
        egregore, 
        request.query, 
        request.max_tokens
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@app.post("/multi-agent")
async def multi_agent_query(request: MultiAgentRequest):
    """Query multiple egregores with optional synthesis"""
    result = await manager.multi_agent_query(
        request.query,
        request.egregores,
        request.synthesize
    )
    return result


if __name__ == "__main__":
    import uvicorn
    
    print("="*70)
    print("S2 EGREGORE SERVICE MANAGER")
    print("="*70)
    print("")
    print("Managing 9 Ninefold Egregores:")
    for name, config in EGREGORES.items():
        print(f"  • {config.name:12} (Port {config.port}) - {config.description}")
    print("")
    print("="*70)
    print("Starting service on http://localhost:9000")
    print("="*70)
    
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
