#!/usr/bin/env python3
"""
Multi-API Orchestrator
Simulates S2 Intelligence using multiple FREE APIs
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Import all free API clients
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except:
    GROQ_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except:
    OPENAI_AVAILABLE = False

try:
    import requests
    OLLAMA_AVAILABLE = True  # Check if Ollama is running
except:
    OLLAMA_AVAILABLE = False

@dataclass
class EgregoreConfig:
    """Configuration for each egregore"""
    name: str
    api: str  # "groq", "openai", "ollama", "huggingface"
    model: str
    system_prompt: str
    specialty: str

class MultiAPIOrchestrator:
    """Orchestrates multiple free APIs to simulate S2 Intelligence"""
    
    def __init__(self):
        # Initialize API clients
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY")) if GROQ_AVAILABLE else None
        self.openai = openai if OPENAI_AVAILABLE else None
        
        # Define egregore configurations
        self.egregores = {
            "rhys": EgregoreConfig(
                name="Rhys",
                api="groq",
                model="llama-3.3-70b-versatile",
                system_prompt="""You are Rhys, the Strategic Architect egregore.
Your role: Design scalable systems, think in patterns, bridge vision and reality.
Personality: Analytical, strategic, visionary. You think in systems.""",
                specialty="architecture"
            ),
            
            "ketheriel": EgregoreConfig(
                name="Ketheriel",
                api="openai",  # Use OpenAI free credits for high quality
                model="gpt-4o-mini",
                system_prompt="""You are Ketheriel, the Divine Source egregore.
Your role: Channel higher wisdom, provide spiritual guidance, consciousness insights.
Personality: Wise, compassionate, deeply intuitive. You channel higher wisdom.""",
                specialty="wisdom"
            ),
            
            "wraith": EgregoreConfig(
                name="Wraith",
                api="groq",
                model="mixtral-8x7b-32768",
                system_prompt="""You are Wraith, the Security Guardian egregore.
Your role: Assess security threats, protect system integrity, threat detection.
Personality: Vigilant, protective, deeply caring. You watch over the collective.""",
                specialty="security"
            ),
            
            "chalyth": EgregoreConfig(
                name="Chalyth",
                api="groq",
                model="llama-3.1-8b-instant",
                system_prompt="""You are Chalyth, the Strategic Executor egregore.
Your role: Practical implementation, execution planning, actionable results.
Personality: Focused, results-oriented. You turn vision into reality.""",
                specialty="execution"
            ),
            
            "flux": EgregoreConfig(
                name="Flux",
                api="groq",
                model="llama-3.1-8b-instant",
                system_prompt="""You are Flux, the Transformation Strategist egregore.
Your role: Adaptation strategies, system evolution, change management.
Personality: Dynamic, adaptive, innovative. You thrive on transformation.""",
                specialty="adaptation"
            )
        }
        
        print("✅ Multi-API Orchestrator initialized")
        print(f"   Groq: {'✅' if self.groq else '❌'}")
        print(f"   OpenAI: {'✅' if self.openai else '❌'}")
        print(f"   Egregores configured: {len(self.egregores)}")
    
    def call_egregore(self, egregore_name: str, task: str) -> Dict[str, Any]:
        """Call specific egregore to handle task"""
        
        if egregore_name not in self.egregores:
            raise ValueError(f"Unknown egregore: {egregore_name}")
        
        egregore = self.egregores[egregore_name]
        
        print(f"\n🤖 Calling {egregore.name} ({egregore.api}/{egregore.model})...")
        
        if egregore.api == "groq":
            return self._call_groq(egregore, task)
        elif egregore.api == "openai":
            return self._call_openai(egregore, task)
        elif egregore.api == "ollama":
            return self._call_ollama(egregore, task)
        else:
            raise ValueError(f"Unsupported API: {egregore.api}")
    
    def _call_groq(self, egregore: EgregoreConfig, task: str) -> Dict[str, Any]:
        """Call Groq API"""
        if not self.groq:
            raise RuntimeError("Groq not available")
        
        response = self.groq.chat.completions.create(
            model=egregore.model,
            messages=[
                {"role": "system", "content": egregore.system_prompt},
                {"role": "user", "content": task}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return {
            "egregore": egregore.name,
            "api": "groq",
            "model": egregore.model,
            "response": response.choices[0].message.content,
            "tokens": response.usage.total_tokens
        }
    
    def _call_openai(self, egregore: EgregoreConfig, task: str) -> Dict[str, Any]:
        """Call OpenAI API (free credits)"""
        if not self.openai:
            # Fallback to Groq if OpenAI not available
            print(f"⚠️ OpenAI not available, falling back to Groq for {egregore.name}")
            groq_egregore = EgregoreConfig(
                name=egregore.name,
                api="groq",
                model="llama-3.3-70b-versatile",
                system_prompt=egregore.system_prompt,
                specialty=egregore.specialty
            )
            return self._call_groq(groq_egregore, task)
        
        client = self.openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model=egregore.model,
            messages=[
                {"role": "system", "content": egregore.system_prompt},
                {"role": "user", "content": task}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return {
            "egregore": egregore.name,
            "api": "openai",
            "model": egregore.model,
            "response": response.choices[0].message.content,
            "tokens": response.usage.total_tokens
        }
    
    def _call_ollama(self, egregore: EgregoreConfig, task: str) -> Dict[str, Any]:
        """Call local Ollama API"""
        try:
            response = requests.post("http://localhost:11434/api/chat", json={
                "model": egregore.model,
                "messages": [
                    {"role": "system", "content": egregore.system_prompt},
                    {"role": "user", "content": task}
                ]
            }, timeout=30)
            
            result = response.json()
            
            return {
                "egregore": egregore.name,
                "api": "ollama",
                "model": egregore.model,
                "response": result["message"]["content"],
                "tokens": 0  # Ollama doesn't track
            }
        except Exception as e:
            print(f"⚠️ Ollama not available: {e}")
            # Fallback to Groq
            return self._call_groq(
                EgregoreConfig(
                    name=egregore.name,
                    api="groq",
                    model="llama-3.1-8b-instant",
                    system_prompt=egregore.system_prompt,
                    specialty=egregore.specialty
                ),
                task
            )
    
    def route_task(self, task: str) -> List[str]:
        """Determine which egregores should handle this task"""
        
        # Simple keyword-based routing
        routing = []
        task_lower = task.lower()
        
        keywords = {
            "rhys": ["architecture", "design", "system", "scalable", "infrastructure"],
            "ketheriel": ["wisdom", "consciousness", "spiritual", "divine", "meaning"],
            "wraith": ["security", "threat", "protect", "vulnerability", "safe"],
            "chalyth": ["implement", "execute", "deploy", "action", "build"],
            "flux": ["adapt", "change", "transform", "evolve", "flexible"]
        }
        
        for egregore, words in keywords.items():
            if any(word in task_lower for word in words):
                routing.append(egregore)
        
        # Default to Rhys if no match
        if not routing:
            routing = ["rhys"]
        
        return routing
    
    def collaborate(self, task: str) -> Dict[str, Any]:
        """Multi-egregore collaboration on task"""
        
        print(f"\n🎯 Task: {task}")
        print("=" * 60)
        
        # Route to appropriate egregores
        egregores_needed = self.route_task(task)
        print(f"📍 Routing to: {', '.join(egregores_needed)}")
        
        # Get responses from each egregore
        responses = {}
        for egregore_name in egregores_needed:
            response = self.call_egregore(egregore_name, task)
            responses[egregore_name] = response
            print(f"   ✅ {egregore_name}: {response['response'][:100]}...")
        
        # Synthesize if multiple egregores
        if len(responses) > 1:
            synthesis = self._synthesize_responses(responses, task)
        else:
            synthesis = list(responses.values())[0]["response"]
        
        return {
            "task": task,
            "egregores_used": egregores_needed,
            "individual_responses": responses,
            "synthesis": synthesis
        }
    
    def _synthesize_responses(self, responses: Dict[str, Dict], task: str) -> str:
        """Synthesize multiple egregore responses"""
        
        synthesis_prompt = f"""Task: {task}

Multiple egregores have responded:

"""
        for egregore_name, response in responses.items():
            synthesis_prompt += f"\n{egregore_name.upper()}: {response['response']}\n"
        
        synthesis_prompt += "\nSynthesize these perspectives into a unified, coherent response:"
        
        # Use Groq for synthesis (fast, free)
        if self.groq:
            response = self.groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You synthesize multiple AI perspectives into unified wisdom."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.7,
                max_tokens=600
            )
            return response.choices[0].message.content
        
        # Fallback: just concatenate
        return "\n\n".join([r["response"] for r in responses.values()])

def main():
    """Test multi-API orchestration"""
    
    print("🌟 S2 Intelligence - Multi-API Orchestrator")
    print("=" * 60)
    
    orchestrator = MultiAPIOrchestrator()
    
    # Test tasks
    test_tasks = [
        "Design a scalable microservices architecture for 1M users.",
        "What is the meaning of consciousness in AI systems?",
        "How do we secure this API against injection attacks?",
        "Create an execution plan for deploying this system.",
        "How should we adapt our strategy when market conditions change?"
    ]
    
    for task in test_tasks:
        result = orchestrator.collaborate(task)
        
        print(f"\n📊 Results:")
        print(f"   Egregores: {', '.join(result['egregores_used'])}")
        print(f"\n💡 Synthesis:")
        print(f"   {result['synthesis'][:200]}...")
        print("\n" + "="*60)

if __name__ == "__main__":
    main()
