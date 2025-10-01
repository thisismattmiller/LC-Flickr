#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import numpy as np

try:
    import umap
    # Test if UMAP class is available
    _ = umap.UMAP
except (ImportError, AttributeError):
    print("Error: UMAP not properly installed.")
    print("Please install it with: pip install umap-learn")
    print("Note: The package name is 'umap-learn', not 'umap'")
    sys.exit(1)

def load_jsonl_data(filepath):
    """Load data from JSONL file."""
    data = []
    embeddings = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                comment = json.loads(line)
                data.append(comment)
                embeddings.append(comment['embedding'])
    
    return data, np.array(embeddings)

def save_jsonl_data(filepath, data):
    """Save data to JSONL file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

def main():
    # Set up paths
    input_file = Path(__file__).parent.parent / 'data' / 'comments_with_embeddings.jsonl'
    output_file = Path(__file__).parent.parent / 'data' / 'comments_with_umap_coords.jsonl'
    
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        print("Please run build_embeddings.py first to generate embeddings.")
        sys.exit(1)
    
    # Delete output file if it exists
    if output_file.exists():
        print(f"Removing existing output file: {output_file}")
        output_file.unlink()
    
    print(f"Loading data from {input_file}...")
    data, embeddings = load_jsonl_data(input_file)
    
    if len(data) == 0:
        print("No data found in input file.")
        sys.exit(1)
    
    print(f"Loaded {len(data)} comments with embeddings")
    print(f"Embedding dimensions: {embeddings.shape}")
    
    # Configure UMAP
    print("\nConfiguring UMAP reducer...")
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=15,
        min_dist=0.05,
        metric='cosine',
        random_state=42,
        verbose=True
    )
    
    # Fit and transform the embeddings
    print("\nReducing embeddings to 2D...")
    coords_2d = reducer.fit_transform(embeddings)
    
    print(f"UMAP reduction complete. Output shape: {coords_2d.shape}")
    
    # Replace embeddings with x,y coordinates
    print("\nReplacing embeddings with 2D coordinates...")
    for i, comment in enumerate(data):
        # Remove the high-dimensional embedding
        del comment['embedding']
        # Add the 2D coordinates
        comment['x'] = float(coords_2d[i, 0])
        comment['y'] = float(coords_2d[i, 1])
    
    # Save the results
    print(f"\nSaving results to {output_file}...")
    save_jsonl_data(output_file, data)
    
    # Print some statistics
    x_coords = coords_2d[:, 0]
    y_coords = coords_2d[:, 1]
    
    print(f"\n✓ Successfully processed {len(data)} comments")
    print(f"Output saved to: {output_file}")
    print(f"\nCoordinate ranges:")
    print(f"  X: [{x_coords.min():.3f}, {x_coords.max():.3f}]")
    print(f"  Y: [{y_coords.min():.3f}, {y_coords.max():.3f}]")

if __name__ == "__main__":
    main()