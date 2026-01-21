#!/usr/bin/env python3
"""
Standard AI Benchmarks via Pythia API
Runs MMLU, HellaSwag, and ARC tests by querying Pythia directly
"""

import requests
import json
import time
from datetime import datetime

# Pythia endpoint
PYTHIA_URL = "http://192.168.1.78:8090/api/generate"

def query_pythia(prompt, max_tokens=100):
    """Query Pythia service"""
    try:
        response = requests.post(
            PYTHIA_URL,
            json={
                'model': 'pythia-1b',
                'prompt': prompt,
                'max_tokens': max_tokens,
                'temperature': 0.0  # Deterministic for benchmarks
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            return result.get('text', result.get('response', result.get('generated_text', '')))
        else:
            return None
    except Exception as e:
        print(f"Error querying Pythia: {e}")
        return None

# Sample MMLU questions (subset for quick test)
MMLU_QUESTIONS = [
    {
        'question': 'What is the capital of France?',
        'choices': ['A) London', 'B) Berlin', 'C) Paris', 'D) Madrid'],
        'answer': 'C',
        'subject': 'geography'
    },
    {
        'question': 'What is 2 + 2?',
        'choices': ['A) 3', 'B) 4', 'C) 5', 'D) 6'],
        'answer': 'B',
        'subject': 'math'
    },
    {
        'question': 'Who wrote "Romeo and Juliet"?',
        'choices': ['A) Charles Dickens', 'B) William Shakespeare', 'C) Jane Austen', 'D) Mark Twain'],
        'answer': 'B',
        'subject': 'literature'
    },
    {
        'question': 'What is the chemical symbol for water?',
        'choices': ['A) H2O', 'B) CO2', 'C) O2', 'D) N2'],
        'answer': 'A',
        'subject': 'chemistry'
    },
    {
        'question': 'What is the largest planet in our solar system?',
        'choices': ['A) Mars', 'B) Earth', 'C) Jupiter', 'D) Saturn'],
        'answer': 'C',
        'subject': 'astronomy'
    },
]

# Sample HellaSwag questions
HELLASWAG_QUESTIONS = [
    {
        'context': 'A woman is seen standing in a kitchen while holding a knife.',
        'endings': [
            'She then begins cutting up vegetables on a cutting board.',
            'She then starts flying through the air.',
            'She then transforms into a dragon.',
            'She then begins building a rocket ship.'
        ],
        'answer': 0
    },
    {
        'context': 'A man is seen speaking to the camera while holding a basketball.',
        'endings': [
            'He then demonstrates how to properly shoot a basketball.',
            'He then starts knitting a sweater.',
            'He then begins to eat the basketball.',
            'He then uses the basketball as a pillow to take a nap.'
        ],
        'answer': 0
    },
]

# Sample ARC-easy questions
ARC_QUESTIONS = [
    {
        'question': 'Which of the following is a renewable energy source?',
        'choices': ['A) Coal', 'B) Oil', 'C) Solar power', 'D) Natural gas'],
        'answer': 'C',
        'grade': '3'
    },
    {
        'question': 'What do plants need to make food?',
        'choices': ['A) Sunlight and water', 'B) Only water', 'C) Only soil', 'D) Only air'],
        'answer': 'A',
        'grade': '3'
    },
]

def run_mmlu_benchmark():
    """Run MMLU benchmark"""
    print("\n" + "="*70)
    print("MMLU (Massive Multitask Language Understanding) BENCHMARK")
    print("="*70)
    print(f"Testing: {len(MMLU_QUESTIONS)} questions (sample)")
    print()
    
    correct = 0
    total = len(MMLU_QUESTIONS)
    results = []
    
    for i, q in enumerate(MMLU_QUESTIONS, 1):
        print(f"[{i}/{total}] {q['subject']}: {q['question']}")
        
        # Format prompt
        prompt = f"{q['question']}\n"
        for choice in q['choices']:
            prompt += f"{choice}\n"
        prompt += "Answer:"
        
        # Query Pythia
        response = query_pythia(prompt, max_tokens=10)
        
        if response:
            # Check if answer is correct (look for letter in response)
            predicted = response.strip().upper()
            if q['answer'] in predicted[:5]:  # Check first few chars
                correct += 1
                status = "[OK]"
            else:
                status = "[X]"
            
            print(f"  Expected: {q['answer']}, Got: {predicted[:20]}... {status}")
            results.append({
                'question': q['question'],
                'expected': q['answer'],
                'predicted': predicted[:50],
                'correct': q['answer'] in predicted[:5]
            })
        else:
            print(f"  [ERROR] No response")
        
        print()
        time.sleep(0.1)  # Rate limiting
    
    accuracy = (correct / total) * 100
    
    print("="*70)
    print(f"MMLU Results: {correct}/{total} ({accuracy:.1f}%)")
    print("="*70)
    print()
    
    return {
        'benchmark': 'MMLU',
        'correct': correct,
        'total': total,
        'accuracy': accuracy,
        'results': results
    }

def run_hellaswag_benchmark():
    """Run HellaSwag benchmark (commonsense reasoning)"""
    print("\n" + "="*70)
    print("HELLASWAG (Commonsense Reasoning) BENCHMARK")
    print("="*70)
    print(f"Testing: {len(HELLASWAG_QUESTIONS)} questions (sample)")
    print()
    
    correct = 0
    total = len(HELLASWAG_QUESTIONS)
    results = []
    
    for i, q in enumerate(HELLASWAG_QUESTIONS, 1):
        print(f"[{i}/{total}] Context: {q['context']}")
        print("  Endings:")
        for j, ending in enumerate(q['endings']):
            print(f"    {j}: {ending}")
        
        # Format prompt - ask model to continue the context
        prompt = f"{q['context']} What happens next?\n\n"
        for j, ending in enumerate(q['endings']):
            prompt += f"{j}. {ending}\n"
        prompt += "\nMost likely continuation:"
        
        # Query Pythia
        response = query_pythia(prompt, max_tokens=20)
        
        if response:
            # Check if response contains correct ending number
            predicted_idx = None
            for j in range(len(q['endings'])):
                if str(j) in response[:10]:
                    predicted_idx = j
                    break
            
            if predicted_idx == q['answer']:
                correct += 1
                status = "[OK]"
            else:
                status = "[X]"
            
            print(f"  Expected: {q['answer']}, Got: {predicted_idx} {status}")
            results.append({
                'context': q['context'],
                'expected': q['answer'],
                'predicted': predicted_idx,
                'correct': predicted_idx == q['answer']
            })
        else:
            print(f"  [ERROR] No response")
        
        print()
        time.sleep(0.1)
    
    accuracy = (correct / total) * 100
    
    print("="*70)
    print(f"HellaSwag Results: {correct}/{total} ({accuracy:.1f}%)")
    print("="*70)
    print()
    
    return {
        'benchmark': 'HellaSwag',
        'correct': correct,
        'total': total,
        'accuracy': accuracy,
        'results': results
    }

def run_arc_benchmark():
    """Run ARC (question answering) benchmark"""
    print("\n" + "="*70)
    print("ARC-EASY (Science Question Answering) BENCHMARK")
    print("="*70)
    print(f"Testing: {len(ARC_QUESTIONS)} questions (sample)")
    print()
    
    correct = 0
    total = len(ARC_QUESTIONS)
    results = []
    
    for i, q in enumerate(ARC_QUESTIONS, 1):
        print(f"[{i}/{total}] Grade {q['grade']}: {q['question']}")
        
        # Format prompt
        prompt = f"{q['question']}\n"
        for choice in q['choices']:
            prompt += f"{choice}\n"
        prompt += "Answer:"
        
        # Query Pythia
        response = query_pythia(prompt, max_tokens=10)
        
        if response:
            # Check if answer is correct
            predicted = response.strip().upper()
            if q['answer'] in predicted[:5]:
                correct += 1
                status = "[OK]"
            else:
                status = "[X]"
            
            print(f"  Expected: {q['answer']}, Got: {predicted[:20]}... {status}")
            results.append({
                'question': q['question'],
                'expected': q['answer'],
                'predicted': predicted[:50],
                'correct': q['answer'] in predicted[:5]
            })
        else:
            print(f"  [ERROR] No response")
        
        print()
        time.sleep(0.1)
    
    accuracy = (correct / total) * 100
    
    print("="*70)
    print(f"ARC-Easy Results: {correct}/{total} ({accuracy:.1f}%)")
    print("="*70)
    print()
    
    return {
        'benchmark': 'ARC-Easy',
        'correct': correct,
        'total': total,
        'accuracy': accuracy,
        'results': results
    }

def main():
    """Run all benchmarks"""
    print("\n" + "="*70)
    print("STANDARD AI BENCHMARKS - PYTHIA 1B")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Model: Pythia-1B (S2-trained)")
    print(f"Endpoint: {PYTHIA_URL}")
    print()
    
    # Test connection
    print("Testing connection to Pythia...")
    test_response = query_pythia("Hello", max_tokens=5)
    if test_response:
        print("[OK] Pythia is responding")
    else:
        print("[ERROR] Cannot connect to Pythia. Exiting.")
        return
    
    # Run benchmarks
    all_results = []
    
    # MMLU
    mmlu_results = run_mmlu_benchmark()
    all_results.append(mmlu_results)
    
    # HellaSwag
    hellaswag_results = run_hellaswag_benchmark()
    all_results.append(hellaswag_results)
    
    # ARC
    arc_results = run_arc_benchmark()
    all_results.append(arc_results)
    
    # Summary
    print("\n" + "="*70)
    print("BENCHMARK SUMMARY")
    print("="*70)
    for result in all_results:
        print(f"{result['benchmark']}: {result['accuracy']:.1f}% ({result['correct']}/{result['total']})")
    print()
    
    # Save results
    output_file = f"results/standard_benchmarks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'date': datetime.now().isoformat(),
            'model': 'Pythia-1B (S2-trained)',
            'results': all_results
        }, f, indent=2)
    
    print(f"Results saved to: {output_file}")
    print()
    
    print("="*70)
    print("BENCHMARK COMPLETE")
    print("="*70)
    print()
    print("NOTE: These are SAMPLE tests with limited questions.")
    print("For official scores, run full benchmarks via lm-evaluation-harness.")
    print("Expected Pythia-1B scores: MMLU ~25-30%, HellaSwag ~40-50%, ARC ~50-60%")

if __name__ == '__main__':
    main()
