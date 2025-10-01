#!/usr/bin/env python3
import json
import sys
import os
from pathlib import Path
from google import genai
from google.genai import types
import numpy as np
import time

def load_data(filepath):
    """Load the comments data from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_processed_ids(jsonl_filepath):
    """Load already processed comment IDs from JSONL file."""
    processed_ids = set()
    if jsonl_filepath.exists():
        with open(jsonl_filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    comment = json.loads(line)
                    processed_ids.add(comment['comment_id'])
    return processed_ids

def append_to_jsonl(filepath, comments_with_embeddings):
    """Append comments with embeddings to JSONL file."""
    with open(filepath, 'a', encoding='utf-8') as f:
        for comment in comments_with_embeddings:
            f.write(json.dumps(comment, ensure_ascii=False) + '\n')

def get_unprocessed_comments(data, processed_ids):
    """Get list of comments that don't have embeddings yet and have non-empty content."""
    return [(i, comment) for i, comment in enumerate(data) 
            if comment['comment_id'] not in processed_ids 
            and comment.get('comment_content', '').strip()]

def process_batch(client, batch_comments):
    """Process a batch of comments and get their embeddings."""
    try:
        batch_texts = [comment['comment_content'] for comment in batch_comments]
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch_texts,
            config=types.EmbedContentConfig(task_type="CLUSTERING")
        )
        
        # Create list of comments with embeddings
        comments_with_embeddings = []
        for comment, embedding in zip(batch_comments, result.embeddings):
            comment_with_embedding = comment.copy()
            comment_with_embedding['embedding'] = embedding.values
            comments_with_embeddings.append(comment_with_embedding)
        
        return comments_with_embeddings
    except Exception as e:
        print(f"Error processing batch: {e}")
        return None

def main():
    # Set up paths
    data_file = Path(__file__).parent.parent / 'data' / 'extracted_comments_for_embedding.json'
    output_file = Path(__file__).parent.parent / 'data' / 'comments_with_embeddings.jsonl'
    
    if not data_file.exists():
        print(f"Error: {data_file} not found")
        sys.exit(1)
    
    print(f"Loading data from {data_file}...")
    data = load_data(data_file)
    total_comments = len(data)
    print(f"Total comments: {total_comments}")
    
    # Load already processed comment IDs from JSONL if it exists
    print(f"Checking for existing progress in {output_file}...")
    processed_ids = load_processed_ids(output_file)
    print(f"Comments already processed: {len(processed_ids)}")
    
    # Get unprocessed comments
    unprocessed = get_unprocessed_comments(data, processed_ids)
    
    # Count how many were skipped due to empty content
    total_unprocessed = len([c for c in data if c['comment_id'] not in processed_ids])
    empty_skipped = total_unprocessed - len(unprocessed)
    
    print(f"Comments to process: {len(unprocessed)}")
    if empty_skipped > 0:
        print(f"Skipping {empty_skipped} comments with empty content")
    
    if not unprocessed:
        print("All comments already have embeddings!")
        return
    
    # Initialize Google AI client
    print("Initializing Google AI client...")
    client = genai.Client(
        api_key=os.environ.get("GOOGLE_GENAI"),
    )
    
    # Process in batches of 100
    batch_size = 100
    total_batches = (len(unprocessed) + batch_size - 1) // batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(unprocessed))
        
        # Get current batch
        batch = unprocessed[start_idx:end_idx]
        batch_comments = [comment for _, comment in batch]
        
        print(f"\nProcessing batch {batch_num + 1}/{total_batches} ({len(batch_comments)} comments)...")
        
        # Process the batch
        comments_with_embeddings = process_batch(client, batch_comments)
        
        if comments_with_embeddings:
            # Append to JSONL file
            print(f"Saving batch {batch_num + 1} to {output_file}...")
            append_to_jsonl(output_file, comments_with_embeddings)
            print(f"Batch {batch_num + 1} completed and saved.")
            
            # Small delay to avoid rate limiting
            if batch_num < total_batches - 1:
                time.sleep(20)
        else:
            print(f"Failed to process batch {batch_num + 1}. You can restart the script to continue.")
            sys.exit(1)
    
    print(f"\n✓ All embeddings generated successfully!")
    print(f"Total comments with embeddings: {len(processed_ids) + len(unprocessed)}")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main()