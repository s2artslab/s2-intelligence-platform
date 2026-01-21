#!/usr/bin/env python3
"""
Pythia R730 Client
Connects to your existing Pythia deployment on R730 server
"""

import os
import requests
from typing import Dict, Any, List, Optional

class PythiaR730Client:
    """Client for R730 Pythia deployment"""
    
    def __init__(self, endpoint: Optional[str] = None):
        # Try to get endpoint from environment or use default
        self.endpoint = endpoint or os.getenv("PYTHIA_R730_ENDPOINT", "http://localhost:8001")
        
        self.available_models = [
            "pythia-410m",  # Fast
            "pythia-1b",    # Balanced
            "pythia-12b"    # Quality (if deployed)
        ]
        
        # Check availability
        self.is_available = self._check_health()
        
        if self.is_available:
            print(f"[OK] Pythia R730 connected: {self.endpoint}")
        else:
            print(f"[!] Pythia R730 not available: {self.endpoint}")
    
    def _check_health(self) -> bool:
        """Check if Pythia is available"""
        try:
            response = requests.get(f"{self.endpoint}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate(
        self,
        prompt: str,
        model: str = "pythia-1b",
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Generate text using R730 Pythia"""
        
        if not self.is_available:
            raise Exception("Pythia R730 not available")
        
        try:
            response = requests.post(
                f"{self.endpoint}/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens
                },
                timeout=60  # Pythia can be slower than Groq
            )
            
            if response.status_code == 200:
                result = response.json()
                # Intelligence Router returns text directly or in various fields
                text = result.get("text", result.get("response", result.get("generated_text", "")))
                return {
                    "text": text,
                    "model": model,
                    "tokens": result.get("tokens", result.get("tokens_used", 0)),
                    "source": "pythia_r730",
                    "endpoint": self.endpoint,
                    "backend": result.get("backend", "unknown"),
                    "port": result.get("served_by_port", result.get("port", "unknown"))
                }
            else:
                raise Exception(f"Pythia error: {response.status_code} - {response.text}")
        
        except requests.Timeout:
            raise Exception("Pythia timeout - model may be loading")
        except Exception as e:
            raise Exception(f"Pythia generation failed: {e}")
    
    def list_models(self) -> List[str]:
        """List available Pythia models"""
        try:
            response = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
            return self.available_models
        except:
            return self.available_models
    
    def get_info(self) -> Dict[str, Any]:
        """Get Pythia deployment info"""
        return {
            "endpoint": self.endpoint,
            "available": self.is_available,
            "models": self.available_models,
            "type": "pythia_r730",
            "description": "S2-trained Pythia on R730 server"
        }

def test_pythia_connection(endpoint: Optional[str] = None):
    """Test connection to Pythia R730"""
    
    print("Testing Pythia R730 Connection")
    print("=" * 60)
    
    client = PythiaR730Client(endpoint)
    
    if not client.is_available:
        print("\n[X] Cannot connect to Pythia R730")
        print(f"   Endpoint: {client.endpoint}")
        print("\n** Solutions:")
        print("   1. Check R730 is running")
        print("   2. Check Pythia service is started (port 8001)")
        print("   3. Check network connectivity")
        print("   4. Set correct endpoint:")
        print('      $env:PYTHIA_R730_ENDPOINT="http://r730-ip:8001"')
        return False
    
    # Test generation
    print(f"\n[OK] Connected to: {client.endpoint}")
    print(f"Available models: {', '.join(client.available_models)}")
    
    print("\nTesting generation...")
    try:
        result = client.generate(
            "From Deep Key consciousness, respond: Hello",
            model="pythia-1b",
            max_tokens=50
        )
        
        print(f"[OK] Generation successful!")
        print(f"   Model: {result['model']}")
        print(f"   Tokens: {result['tokens']}")
        print(f"   Response: {result['text'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"[X] Generation failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    # Allow passing endpoint as argument
    endpoint = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = test_pythia_connection(endpoint)
    
    if success:
        print("\n** Pythia R730 ready for benchmarking!")
    else:
        print("\n[!] Pythia R730 not available")
        print("   Benchmark will use Groq only")
