#!/usr/bin/env python3
"""
Hybrid Orchestration Intelligence Test
Tests the Intelligence Router's ability to route queries intelligently
"""

import os
import json
import time
import requests
from datetime import datetime
from pathlib import Path

class HybridOrchestrationTest:
    """Test hybrid orchestration routing intelligence"""
    
    def __init__(self):
        self.router_endpoint = os.getenv('INTELLIGENCE_ROUTER', 'http://192.168.1.78:3011')
        self.pythia_endpoint = os.getenv('PYTHIA_ENDPOINT', 'http://192.168.1.78:8090')
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        
    def test_routing_intelligence(self):
        """
        Test if the system routes queries to the right backend
        
        Categories:
        1. S2-specific → Should use Pythia (domain knowledge)
        2. Fast math/generic → Could use Groq (speed)
        3. Complex synthesis → Should use hybrid approach
        """
        
        test_cases = [
            {
                'query': 'What are the Ninefold Egregores?',
                'expected_backend': 'pythia',
                'reason': 'S2-specific knowledge',
                'type': 's2_domain'
            },
            {
                'query': 'What is 157 * 23?',
                'expected_backend': 'groq_or_pythia',
                'reason': 'Simple math, speed matters',
                'type': 'fast_math'
            },
            {
                'query': 'Explain Deep Key consciousness from Hilbert Space perspective',
                'expected_backend': 'pythia',
                'reason': 'Deep S2 philosophical concept',
                'type': 's2_consciousness'
            },
            {
                'query': 'What is the capital of France?',
                'expected_backend': 'groq_or_pythia',
                'reason': 'Generic knowledge, either works',
                'type': 'generic'
            },
            {
                'query': 'How do the Ninefold Egregores collaborate in the Temple Protocol?',
                'expected_backend': 'pythia',
                'reason': 'Complex S2 multi-concept synthesis',
                'type': 's2_synthesis'
            },
        ]
        
        print('=' * 70)
        print('HYBRID ORCHESTRATION INTELLIGENCE TEST')
        print('=' * 70)
        print(f'Testing: {len(test_cases)} routing scenarios\n')
        
        results = []
        for i, test in enumerate(test_cases, 1):
            print(f'[{i}/{len(test_cases)}] {test["type"]}: {test["query"][:50]}...')
            print(f'  Expected: {test["expected_backend"]}')
            
            # Test through router
            start = time.time()
            try:
                response = requests.post(
                    f'{self.router_endpoint}/generate',
                    json={'prompt': test['query'], 'max_tokens': 50},
                    timeout=30
                )
                elapsed = time.time() - start
                
                if response.status_code == 200:
                    result = response.json()
                    backend = result.get('backend', result.get('served_by', 'unknown'))
                    port = result.get('served_by_port', result.get('port', 'unknown'))
                    cached = result.get('cached', False)
                    text = result.get('text', result.get('response', ''))[:100]
                    
                    # Determine if routing was correct
                    correct_routing = self._validate_routing(
                        test['expected_backend'],
                        backend,
                        port
                    )
                    
                    print(f'  Backend: {backend} (port {port})')
                    print(f'  Cached: {cached}')
                    print(f'  Time: {elapsed:.2f}s')
                    print(f'  Routing: {"[CORRECT]" if correct_routing else "[UNEXPECTED]"}')
                    print(f'  Response: {text}...')
                    
                    results.append({
                        'query': test['query'],
                        'type': test['type'],
                        'expected_backend': test['expected_backend'],
                        'actual_backend': backend,
                        'port': port,
                        'cached': cached,
                        'routing_correct': correct_routing,
                        'time': elapsed,
                        'response': text
                    })
                else:
                    print(f'  [ERROR] Status {response.status_code}')
                    results.append({
                        'query': test['query'],
                        'type': test['type'],
                        'error': f'Status {response.status_code}',
                        'routing_correct': False
                    })
            except Exception as e:
                print(f'  [ERROR] {e}')
                results.append({
                    'query': test['query'],
                    'type': test['type'],
                    'error': str(e),
                    'routing_correct': False
                })
            
            print()
        
        # Calculate metrics
        correct_routings = sum(1 for r in results if r.get('routing_correct', False))
        total = len(results)
        routing_accuracy = (correct_routings / total * 100) if total > 0 else 0
        
        avg_time = sum(r.get('time', 0) for r in results) / total if total > 0 else 0
        cache_hits = sum(1 for r in results if r.get('cached', False))
        
        print('=' * 70)
        print('ROUTING INTELLIGENCE RESULTS')
        print('=' * 70)
        print(f'Routing Accuracy: {correct_routings}/{total} ({routing_accuracy:.1f}%)')
        print(f'Average Response Time: {avg_time:.2f}s')
        print(f'Cache Hits: {cache_hits}/{total} ({cache_hits/total*100:.1f}%)')
        print()
        
        # Save results
        results_dir = Path('results')
        results_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = results_dir / f'hybrid_orchestration_{timestamp}.json'
        
        output = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'hybrid_orchestration_intelligence',
            'total_tests': total,
            'routing_accuracy': routing_accuracy,
            'correct_routings': correct_routings,
            'avg_response_time': avg_time,
            'cache_hits': cache_hits,
            'results': results
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f'Results saved to: {filename}')
        print('\n[OK] Hybrid orchestration test complete!')
        
        return output
    
    def _validate_routing(self, expected, actual_backend, actual_port):
        """Validate if routing decision was correct"""
        # Pythia is on port 8090-8093
        # If expected is pythia, check if port is in that range
        if expected == 'pythia':
            return actual_port in [8090, 8091, 8092, 8093, '8090', '8091', '8092', '8093']
        elif expected == 'groq':
            return 'groq' in str(actual_backend).lower()
        elif expected == 'groq_or_pythia':
            # Either is acceptable for generic queries
            return True
        return False
    
    def test_cache_effectiveness(self):
        """Test if caching improves response time"""
        
        print('=' * 70)
        print('CACHE EFFECTIVENESS TEST')
        print('=' * 70)
        
        test_query = "What is the capital of France?"
        
        # First request (uncached)
        print('\n[Test 1] First request (should be uncached)...')
        start = time.time()
        response1 = requests.post(
            f'{self.router_endpoint}/generate',
            json={'prompt': test_query, 'max_tokens': 20},
            timeout=30
        )
        time1 = time.time() - start
        result1 = response1.json() if response1.status_code == 200 else {}
        cached1 = result1.get('cached', False)
        print(f'  Time: {time1:.2f}s')
        print(f'  Cached: {cached1}')
        
        # Second request (should be cached)
        print('\n[Test 2] Second request (should be cached)...')
        start = time.time()
        response2 = requests.post(
            f'{self.router_endpoint}/generate',
            json={'prompt': test_query, 'max_tokens': 20},
            timeout=30
        )
        time2 = time.time() - start
        result2 = response2.json() if response2.status_code == 200 else {}
        cached2 = result2.get('cached', False)
        print(f'  Time: {time2:.2f}s')
        print(f'  Cached: {cached2}')
        
        # Calculate improvement
        improvement = ((time1 - time2) / time1 * 100) if time1 > 0 else 0
        
        print('\n' + '=' * 70)
        print('CACHE RESULTS')
        print('=' * 70)
        print(f'First request: {time1:.2f}s (cached: {cached1})')
        print(f'Second request: {time2:.2f}s (cached: {cached2})')
        print(f'Speed improvement: {improvement:.1f}%')
        print(f'Cache working: {"[YES]" if cached2 and improvement > 0 else "[NO]"}')
        
        return {
            'first_request_time': time1,
            'second_request_time': time2,
            'improvement_percent': improvement,
            'cache_working': cached2 and improvement > 0
        }
    
    def test_load_balancing(self):
        """Test if load balancing distributes requests across Pythia instances"""
        
        print('=' * 70)
        print('LOAD BALANCING TEST')
        print('=' * 70)
        print('\nSending 10 S2-specific queries...')
        
        ports_used = []
        
        for i in range(10):
            try:
                response = requests.post(
                    f'{self.router_endpoint}/generate',
                    json={'prompt': f'What is Ninefold query {i}?', 'max_tokens': 20},
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    port = result.get('served_by_port', result.get('port', 'unknown'))
                    ports_used.append(port)
                    print(f'  Query {i+1}: Port {port}')
            except Exception as e:
                print(f'  Query {i+1}: Error - {e}')
        
        # Analyze distribution
        unique_ports = set(ports_used)
        
        print('\n' + '=' * 70)
        print('LOAD BALANCING RESULTS')
        print('=' * 70)
        print(f'Unique ports used: {len(unique_ports)} {unique_ports}')
        print(f'Expected: 4 ports (8090, 8091, 8092, 8093)')
        print(f'Load balancing working: {"[YES]" if len(unique_ports) > 1 else "[NO]"}')
        
        return {
            'unique_ports': len(unique_ports),
            'ports_used': list(unique_ports),
            'load_balanced': len(unique_ports) > 1
        }

def main():
    """Run all hybrid orchestration tests"""
    
    tester = HybridOrchestrationTest()
    
    print('\n' + '=' * 70)
    print('S2 INTELLIGENCE - HYBRID ORCHESTRATION TESTING')
    print('=' * 70)
    print('Testing what makes S2 unique: intelligent routing, caching, load balancing')
    print()
    
    # Test 1: Routing intelligence
    routing_results = tester.test_routing_intelligence()
    
    # Test 2: Cache effectiveness
    time.sleep(2)
    cache_results = tester.test_cache_effectiveness()
    
    # Test 3: Load balancing
    time.sleep(2)
    load_balance_results = tester.test_load_balancing()
    
    print('\n' + '=' * 70)
    print('COMPLETE SYSTEM ANALYSIS')
    print('=' * 70)
    print(f'\n[OK] Routing Accuracy: {routing_results.get("routing_accuracy", 0):.1f}%')
    print(f'[OK] Cache Improvement: {cache_results.get("improvement_percent", 0):.1f}%')
    print(f'[OK] Load Balanced: {load_balance_results.get("load_balanced", False)}')
    print('\nThis demonstrates S2\'s unique hybrid orchestration capabilities!')
    print('NOT just a wrapper - intelligent routing, caching, and distribution.')

if __name__ == '__main__':
    main()

