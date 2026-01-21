#!/usr/bin/env python3
"""
Download MMLU Sample Dataset
Downloads first 100 questions from MMLU philosophy subset for pilot testing
"""

import requests
import json
import csv
from pathlib import Path

def download_mmlu_sample(output_file="mmlu_sample_100.jsonl", num_questions=100):
    """Download MMLU philosophy questions and format for Together.ai"""
    print("📥 Downloading MMLU Sample Dataset")
    print("=" * 60)
    
    # MMLU philosophy dataset URL
    url = "https://raw.githubusercontent.com/hendrycks/test/master/data/val/philosophy.csv"
    
    try:
        print(f"🌐 Fetching from: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        lines = response.text.strip().split('\n')
        print(f"✅ Downloaded {len(lines)} total questions")
        
        # Parse CSV and convert to JSONL
        questions = []
        reader = csv.reader(lines)
        
        for i, row in enumerate(reader):
            if i >= num_questions:
                break
                
            if len(row) >= 6:
                question = row[0]
                choices = [row[j] for j in range(1, 5)]
                answer = row[5]
                
                # Create prompt in Together.ai format
                prompt = f"""Question: {question}

Choices:
A) {choices[0]}
B) {choices[1]}
C) {choices[2]}
D) {choices[3]}

Answer with ONLY the letter (A, B, C, or D):"""
                
                questions.append({
                    "prompt": prompt,
                    "reference_answer": answer,
                    "category": "philosophy",
                    "question_id": f"mmlu_phil_{i:03d}",
                    "question_text": question,
                    "choices": {
                        "A": choices[0],
                        "B": choices[1],
                        "C": choices[2],
                        "D": choices[3]
                    }
                })
        
        # Save as JSONL
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for q in questions:
                f.write(json.dumps(q, ensure_ascii=False) + "\n")
        
        print(f"✅ Saved {len(questions)} questions to: {output_file}")
        print(f"📊 Category: Philosophy")
        print(f"📝 Format: JSONL (Together.ai compatible)")
        
        # Print sample question
        if questions:
            print("\n📋 Sample Question:")
            print("-" * 60)
            sample = questions[0]
            print(f"ID: {sample['question_id']}")
            print(f"Question: {sample['question_text'][:100]}...")
            print(f"Correct Answer: {sample['reference_answer']}")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ Failed to download MMLU dataset: {e}")
        return False
    except Exception as e:
        print(f"❌ Error processing dataset: {e}")
        return False

def download_additional_categories(categories=None, questions_per_category=50):
    """Download multiple MMLU categories"""
    if categories is None:
        categories = [
            "philosophy",
            "computer_science",
            "mathematics",
            "psychology",
            "world_religions"
        ]
    
    print(f"\n📥 Downloading {len(categories)} MMLU Categories")
    print("=" * 60)
    
    all_questions = []
    base_url = "https://raw.githubusercontent.com/hendrycks/test/master/data/val"
    
    for category in categories:
        try:
            url = f"{base_url}/{category}.csv"
            print(f"\n🌐 Fetching {category}...")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            reader = csv.reader(lines)
            
            category_count = 0
            for i, row in enumerate(reader):
                if category_count >= questions_per_category:
                    break
                    
                if len(row) >= 6:
                    question = row[0]
                    choices = [row[j] for j in range(1, 5)]
                    answer = row[5]
                    
                    prompt = f"""Question: {question}

Choices:
A) {choices[0]}
B) {choices[1]}
C) {choices[2]}
D) {choices[3]}

Answer with ONLY the letter (A, B, C, or D):"""
                    
                    all_questions.append({
                        "prompt": prompt,
                        "reference_answer": answer,
                        "category": category,
                        "question_id": f"mmlu_{category}_{i:03d}",
                        "question_text": question,
                        "choices": {
                            "A": choices[0],
                            "B": choices[1],
                            "C": choices[2],
                            "D": choices[3]
                        }
                    })
                    category_count += 1
            
            print(f"✅ {category}: {category_count} questions")
            
        except Exception as e:
            print(f"⚠️ {category}: Failed ({e})")
            continue
    
    # Save combined dataset
    output_file = f"mmlu_multi_category_{len(all_questions)}.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for q in all_questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    
    print(f"\n✅ Total questions saved: {len(all_questions)}")
    print(f"📄 File: {output_file}")
    
    return True

if __name__ == "__main__":
    print("🔬 MMLU Dataset Downloader for S2 Intelligence Benchmarking")
    print("=" * 60)
    
    # Download single category pilot (100 questions)
    print("\n1️⃣ Downloading pilot dataset (100 questions)...")
    download_mmlu_sample()
    
    # Download multi-category dataset (250 questions)
    print("\n\n2️⃣ Downloading multi-category dataset (250 questions)...")
    download_additional_categories()
    
    print("\n\n🎉 Dataset download complete!")
    print("\n📊 Next steps:")
    print("1. Run: python upload_dataset.py")
    print("2. Run: python run_evaluation.py")
