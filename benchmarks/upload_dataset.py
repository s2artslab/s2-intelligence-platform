#!/usr/bin/env python3
"""
Upload Dataset to Together.ai
Uploads MMLU datasets to Together.ai for evaluation
"""

import os
import json
from pathlib import Path
from typing import Optional

try:
    import together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False
    print("⚠️ Together SDK not installed. Run: pip install together")

def upload_dataset(dataset_file: str, purpose: str = "eval") -> Optional[str]:
    """Upload dataset file to Together.ai"""
    
    if not TOGETHER_AVAILABLE:
        print("❌ Together SDK not available")
        return None
    
    print(f"📤 Uploading Dataset to Together.ai")
    print("=" * 60)
    
    # Check API key
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("❌ TOGETHER_API_KEY environment variable not set")
        print("\n💡 To set your API key:")
        print("   Windows PowerShell: $env:TOGETHER_API_KEY=\"your-key-here\"")
        print("   Linux/Mac: export TOGETHER_API_KEY=\"your-key-here\"")
        return None
    
    together.api_key = api_key
    
    # Check if file exists
    if not Path(dataset_file).exists():
        print(f"❌ File not found: {dataset_file}")
        return None
    
    # Get file stats
    file_size = Path(dataset_file).stat().st_size
    with open(dataset_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        num_questions = len(lines)
    
    print(f"📄 File: {dataset_file}")
    print(f"📊 Questions: {num_questions}")
    print(f"💾 Size: {file_size:,} bytes")
    
    try:
        print(f"\n🚀 Uploading to Together.ai...")
        
        # Upload file
        with open(dataset_file, "rb") as f:
            file_response = together.Files.create(
                file=f,
                purpose=purpose
            )
        
        print(f"✅ Upload successful!")
        print(f"📝 File ID: {file_response.id}")
        print(f"📅 Created: {file_response.created_at}")
        print(f"📊 Purpose: {file_response.purpose}")
        
        # Save file ID for later use
        file_id_path = f"{dataset_file}.file_id"
        with open(file_id_path, "w") as f:
            f.write(file_response.id)
        
        print(f"\n💾 File ID saved to: {file_id_path}")
        
        return file_response.id
        
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None

def list_uploaded_files():
    """List all uploaded files"""
    
    if not TOGETHER_AVAILABLE:
        print("❌ Together SDK not available")
        return
    
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("❌ TOGETHER_API_KEY not set")
        return
    
    together.api_key = api_key
    
    try:
        print("\n📋 Listing Uploaded Files")
        print("=" * 60)
        
        files = together.Files.list()
        
        if not files.data:
            print("⚠️ No files found")
            return
        
        print(f"Found {len(files.data)} files:\n")
        
        for file in files.data:
            print(f"📄 {file.filename}")
            print(f"   ID: {file.id}")
            print(f"   Size: {file.bytes:,} bytes")
            print(f"   Created: {file.created_at}")
            print(f"   Purpose: {file.purpose}")
            print()
        
    except Exception as e:
        print(f"❌ Failed to list files: {e}")

def delete_file(file_id: str):
    """Delete a file from Together.ai"""
    
    if not TOGETHER_AVAILABLE:
        print("❌ Together SDK not available")
        return
    
    api_key = os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("❌ TOGETHER_API_KEY not set")
        return
    
    together.api_key = api_key
    
    try:
        print(f"\n🗑️ Deleting file: {file_id}")
        together.Files.delete(file_id)
        print("✅ File deleted successfully")
        
    except Exception as e:
        print(f"❌ Failed to delete file: {e}")

if __name__ == "__main__":
    print("📤 Together.ai Dataset Uploader for S2 Intelligence")
    print("=" * 60)
    
    import sys
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_uploaded_files()
        elif sys.argv[1] == "delete" and len(sys.argv) > 2:
            delete_file(sys.argv[2])
        else:
            dataset_file = sys.argv[1]
            upload_dataset(dataset_file)
    else:
        # Default: upload pilot dataset
        datasets_to_upload = [
            "mmlu_sample_100.jsonl",
            "mmlu_multi_category_250.jsonl"
        ]
        
        uploaded_ids = []
        
        for dataset in datasets_to_upload:
            if Path(dataset).exists():
                file_id = upload_dataset(dataset)
                if file_id:
                    uploaded_ids.append((dataset, file_id))
            else:
                print(f"\n⚠️ Skipping {dataset} (not found)")
                print(f"   Run: python download_mmlu_sample.py")
        
        if uploaded_ids:
            print("\n\n✅ Upload Summary")
            print("=" * 60)
            for dataset, file_id in uploaded_ids:
                print(f"📄 {dataset}")
                print(f"   File ID: {file_id}")
            
            print("\n📊 Next steps:")
            print("1. Run: python run_evaluation.py")
            print("2. Or use file IDs in custom evaluation scripts")
