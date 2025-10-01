#!/usr/bin/env python3
import json
import pandas as pd
from pathlib import Path
import sys

def convert_jsonl_to_parquet(input_file, output_file):
    """Convert JSONL file to Parquet format."""
    
    print(f"Reading JSONL file: {input_file}")
    
    # Read all records from JSONL file
    records = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    record = json.loads(line)
                    records.append(record)
                    if line_num % 10000 == 0:
                        print(f"  Processed {line_num:,} lines...")
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {line_num}: {e}")
                    continue
    
    print(f"Total records loaded: {len(records):,}")
    
    if not records:
        print("No valid records found in the input file.")
        return
    
    # Create DataFrame from records
    print("Creating DataFrame...")
    df = pd.DataFrame(records)
    
    # Display DataFrame info
    print("\nDataFrame Info:")
    print(f"  Shape: {df.shape}")
    print(f"  Columns: {', '.join(df.columns)}")
    print("\nData types:")
    for col in df.columns:
        print(f"  {col}: {df[col].dtype}")
    
    # Show category info if present
    if 'category' in df.columns:
        unique_categories = df['category'].nunique()
        category_counts = df['category'].value_counts()
        print(f"\nCategory Statistics:")
        print(f"  Unique categories: {unique_categories}")
        print(f"  Top 5 categories:")
        for cat, count in category_counts.head(5).items():
            print(f"    Category {cat}: {count:,} comments ({count/len(df)*100:.1f}%)")
        if -1 in df['category'].values:
            unclustered = (df['category'] == -1).sum()
            print(f"  Unclustered points (-1): {unclustered:,} ({unclustered/len(df)*100:.1f}%)")
    
    # Show sample data
    print("\nFirst 3 records:")
    print(df.head(3))
    
    # Write to Parquet file
    print(f"\nWriting Parquet file: {output_file}")
    df.to_parquet(
        output_file,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    
    # Verify the output file
    output_size = Path(output_file).stat().st_size
    print(f"✓ Parquet file created successfully")
    print(f"  File size: {output_size / 1024 / 1024:.2f} MB")
    
    # Test reading the Parquet file
    print("\nVerifying Parquet file...")
    df_test = pd.read_parquet(output_file)
    print(f"  Records in Parquet: {len(df_test):,}")
    print(f"  Columns verified: {list(df_test.columns)}")
    
    return df

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    
    # Try to use the file with categories first, fall back to coordinates only
    input_file = data_dir / 'comments_with_categories.jsonl'
    if not input_file.exists():
        print(f"Note: {input_file.name} not found, trying comments_with_umap_coords.jsonl...")
        input_file = data_dir / 'comments_with_umap_coords.jsonl'
        output_file = data_dir / 'comments_with_umap_coords.parquet'
    else:
        output_file = data_dir / 'comments_with_categories.parquet'
    
    # Check if input file exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Please ensure either 'comments_with_categories.jsonl' or 'comments_with_umap_coords.jsonl' exists in the data directory.")
        sys.exit(1)
    
    # Check if output file already exists
    if output_file.exists():
        response = input("Output file already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Conversion cancelled.")
            sys.exit(0)
        print(f"Removing existing file: {output_file}")
        output_file.unlink()
    
    try:
        # Perform the conversion
        df = convert_jsonl_to_parquet(input_file, output_file)
        
        print("\n" + "="*50)
        print("CONVERSION COMPLETE")
        print("="*50)
        print(f"\nInput:  {input_file}")
        print(f"Output: {output_file}")
        
        # Show file size comparison
        input_size = input_file.stat().st_size
        output_size = output_file.stat().st_size
        compression_ratio = (1 - output_size/input_size) * 100
        
        print(f"\nFile sizes:")
        print(f"  JSONL:   {input_size / 1024 / 1024:.2f} MB")
        print(f"  Parquet: {output_size / 1024 / 1024:.2f} MB")
        print(f"  Compression: {compression_ratio:.1f}% reduction")
        
    except Exception as e:
        print(f"\nError during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()