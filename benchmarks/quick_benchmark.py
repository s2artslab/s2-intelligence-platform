import requests

URL = "http://localhost:8090/api/generate"

print("Quick Benchmark Test - Pythia 1B")
print("="*50)

# Test connection
print("\n1. Testing connection...")
try:
    resp = requests.post(URL, json={"model": "pythia-1b", "prompt": "Hello", "max_tokens": 5}, timeout=10)
    print(f"   Status: {resp.status_code}")
    if resp.status_code == 200:
        print("   [OK] Pythia responding")
    else:
        print("   [ERROR] Bad status")
        exit(1)
except Exception as e:
    print(f"   [ERROR] {e}")
    exit(1)

# Quick MMLU test
print("\n2. MMLU Sample (3 questions)...")
questions = [
    ("What is the capital of France?", "Paris"),
    ("What is 2+2?", "4"),
    ("Who wrote Romeo and Juliet?", "Shakespeare")
]

correct = 0
for i, (q, expected) in enumerate(questions, 1):
    print(f"\n   [{i}/3] {q}")
    try:
        resp = requests.post(URL, json={"model": "pythia-1b", "prompt": q + " Answer:", "max_tokens": 20}, timeout=10)
        if resp.status_code == 200:
            answer = resp.json().get("text", "")
            print(f"   Response: {answer[:80]}")
            if expected.lower() in answer.lower():
                correct += 1
                print("   [OK]")
            else:
                print("   [X]")
    except Exception as e:
        print(f"   [ERROR] {e}")

accuracy = (correct / len(questions)) * 100
print(f"\n3. Results:")
print(f"   Accuracy: {correct}/{len(questions)} ({accuracy:.1f}%)")
print("\n" + "="*50)
print("Benchmark complete!")
