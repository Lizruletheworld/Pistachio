#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Text Summarization Tool using Qwen3 Model
Recursively processes all .txt files in a directory and generates summaries
"""

import os
import glob
import time
import argparse
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

def load_qwen_model(model_path):
    """Load Qwen3 model and tokenizer"""
    print(f"Loading model from: {model_path}")
    
    # Check GPU availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    if device == "cpu":
        print("WARNING: GPU not detected. Running on CPU will be slow!")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_path, 
        trust_remote_code=True
    )
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True
    )
    
    print("Model loaded successfully!")
    return model, tokenizer, device

def generate_summary(model, tokenizer, device, content):
    """Generate summary using Qwen3 model"""
    
    # Build prompt for summary generation
    system_prompt = """You are a professional content analyst. Generate a concise and accurate summary based on the given text.

Requirements:
1. Summarize the main content in 2-3 sentences
2. Keep the key information and main points
3. Use clear and objective language
4. Output the summary directly without additional explanations"""

    user_prompt = f"Please generate a concise summary for the following text:\n\n{content}"
    
    # Build conversation format
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Apply chat template
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Tokenize
    model_inputs = tokenizer([text], return_tensors="pt").to(device)
    
    # Generate response
    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=512,
            do_sample=True,
            temperature=0.7,
            top_p=0.8,
            pad_token_id=tokenizer.eos_token_id
        )
    
    # Decode generated text
    generated_ids = [
        output_ids[len(input_ids):] 
        for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return response.strip()

def find_all_txt_files(root_dir, exclude_summary=True):
    """Recursively find all .txt files"""
    txt_files = []
    
    # Recursively find all .txt files
    pattern = os.path.join(root_dir, "**", "*.txt")
    files = glob.glob(pattern, recursive=True)
    
    # Filter out summary files if needed
    if exclude_summary:
        files = [f for f in files if not os.path.basename(f).startswith('summary_')]
    
    return files

def get_summary_filename(original_file):
    """Generate summary filename based on original filename"""
    dir_path = os.path.dirname(original_file)
    filename = os.path.basename(original_file)
    
    # Generate summary filename: summary_original_name.txt
    name_without_ext = os.path.splitext(filename)[0]
    summary_filename = f"summary_{name_without_ext}.txt"
    
    return os.path.join(dir_path, summary_filename)

def process_all_files(root_dir, model_path):
    """Process all .txt files and generate summaries"""
    
    # Check if directory exists
    if not os.path.exists(root_dir):
        print(f"ERROR: Directory does not exist: {root_dir}")
        return
    
    print(f"Scanning directory: {root_dir}")
    
    # Load model
    model, tokenizer, device = load_qwen_model(model_path)
    
    # Find all .txt files
    txt_files = find_all_txt_files(root_dir)
    total_files = len(txt_files)
    
    if total_files == 0:
        print(f"No .txt files found")
        return
    
    print(f"\nFound {total_files} .txt files to process")
    print("=" * 60)
    
    processed = 0
    skipped = 0
    errors = 0
    
    for i, txt_file in enumerate(txt_files, 1):
        try:
            # Get summary file path
            summary_file = get_summary_filename(txt_file)
            
            # Skip if summary already exists
            if os.path.exists(summary_file):
                print(f"[{i}/{total_files}] Skipped (already exists): {txt_file}")
                skipped += 1
                continue
            
            print(f"\n[{i}/{total_files}] Processing: {txt_file}")
            
            # Read file content
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                print(f"  WARNING: File is empty, skipping")
                skipped += 1
                continue
            
            print(f"  Original length: {len(content)} characters")
            
            # Generate summary
            print(f"  Generating summary...")
            start_time = time.time()
            summary = generate_summary(model, tokenizer, device, content)
            elapsed = time.time() - start_time
            
            # Write summary file
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            
            print(f"  Summary saved: {summary_file}")
            print(f"  Summary length: {len(summary)} characters")
            print(f"  Time elapsed: {elapsed:.2f}s")
            print(f"  Preview: {summary[:150]}{'...' if len(summary) > 150 else ''}")
            
            processed += 1
            
            # Add small delay to avoid GPU overload
            time.sleep(0.1)
            
        except Exception as e:
            print(f"  ERROR: Processing failed: {str(e)}")
            errors += 1
            import traceback
            traceback.print_exc()
            continue
    
    # Print statistics
    print("\n" + "=" * 60)
    print("Processing complete!")
    print("=" * 60)
    print(f"Successfully processed: {processed} files")
    print(f"Skipped: {skipped} files")
    print(f"Failed: {errors} files")
    print(f"Total: {total_files} files")
    print("=" * 60)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Batch text summarization tool using Qwen3-8B model"
    )
    
    parser.add_argument(
        "--input_dir",
        type=str,
        required=True,
        help="Input directory path (will recursively process all .txt files)"
    )
    
    parser.add_argument(
        "--model_path",
        type=str,
        default="/home/intern/lijie/Qwen3-8B",
        help="Model path (default: /home/intern/lijie/Qwen3-8B)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Qwen3-8B Batch Summarization Tool")
    print("=" * 60)
    print(f"Input directory: {args.input_dir}")
    print(f"Model path: {args.model_path}")
    print("=" * 60)
    
    try:
        process_all_files(args.input_dir, args.model_path)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user, exiting...")
    except Exception as e:
        print(f"\n\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()