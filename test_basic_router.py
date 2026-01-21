#!/usr/bin/env python3
"""
Test script for basic open-source router
"""

import requests
import json

BASE_URL = "http://localhost:3011"

def test_router():
    print("=" * 60)
    print("S2 Intelligence Router - Basic Test")
    print("Community Edition (Open Source)")
    print("=" * 60)
    print()
    
    # Test 1: Status check
    print("Test 1: Status Check")
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        if response.status_code == 200:
            status = response.json()
            print(f"✓ Router is running")
            print(f"  Edition: {status['edition']}")
            print(f"  Version: {status['version']}")
            print(f"  Backends: {', '.join(status['backends'])}")
        else:
            print(f"✗ Status check failed: {response.status_code}")
            return
    except requests.exceptions.ConnectionError:
        print("✗ Router is not running. Start it with:")
        print("  python intelligence_router.py")
        return
    
    print()
    
    # Test 2: Basic routing
    print("Test 2: Basic Query Routing")
    
    queries = [
        "What are the Ninefold Egregores?",
        "What is 2+2?",
        "Explain Deep Key consciousness"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n  Query {i}: {query[:50]}...")
        
        response = requests.post(
            f"{BASE_URL}/api/query",
            json={"query": query}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  → Routed to: {result['backend']}")
            print(f"  ✓ Success")
        else:
            print(f"  ✗ Failed: {response.status_code}")
    
    print()
    print("=" * 60)
    print("BASIC TEST COMPLETE")
    print("=" * 60)
    print()
    print("This is the open-source version with basic routing.")
    print()
    print("For advanced features including:")
    print("  • Consciousness tracking (100% accuracy)")
    print("  • Trained S2-domain models (4x advantage)")
    print("  • Advanced semantic routing")
    print("  • Multi-agent orchestration")
    print()
    print("Upgrade to S2 Intelligence Premium")
    print("Contact: beta@s2intelligence.com")
    print()

if __name__ == "__main__":
    test_router()
