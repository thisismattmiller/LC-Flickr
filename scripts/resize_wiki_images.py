#!/usr/bin/env python3

import os
import json
from pathlib import Path
from PIL import Image
import io
import shutil

def resize_image_to_target_size(image_path, target_size_kb=3, max_width=100, max_height=150):
    """
    Resize an image to be at or under target_size_kb and within max dimensions.
    Uses iterative approach to find the right quality/dimensions.
    """
    target_size_bytes = target_size_kb * 1024
    
    # Open the image
    img = Image.open(image_path)
    
    # Convert RGBA to RGB if necessary
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Start with original dimensions
    width, height = img.size
    
    # Calculate scale to fit within max dimensions
    scale_to_fit = min(max_width / width, max_height / height, 1.0)
    
    # Store the best valid result (under target KB)
    best_result = None
    best_size = float('inf')
    
    # Try different combinations of scale and quality
    scales = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1, 0.08, 0.06, 0.04]
    qualities = [95, 85, 75, 65, 55, 45, 35, 25, 20, 15, 10, 5]
    
    for scale in scales:
        for quality in qualities:
            # Apply current scale, but never exceed max dimensions
            actual_scale = min(scale, scale_to_fit)
            new_width = int(width * actual_scale)
            new_height = int(height * actual_scale)
            
            # Ensure we don't exceed max dimensions
            if new_width > max_width or new_height > max_height:
                new_width = min(new_width, max_width)
                new_height = min(new_height, max_height)
            
            # Don't let dimensions get too small
            if new_width < 20 or new_height < 20:
                new_width = max(20, new_width)
                new_height = max(20, new_height)
            
            # Resize image
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save to bytes buffer to check size
            buffer = io.BytesIO()
            resized.save(buffer, format='JPEG', quality=quality, optimize=True)
            size = buffer.tell()
            
            # If it's under the limit and closer to target than our best, keep it
            if size <= target_size_bytes:
                if best_result is None or (target_size_bytes - size) < (target_size_bytes - best_size):
                    best_result = buffer.getvalue()
                    best_size = size
                    # If we're within 90% of target, that's good enough
                    if size >= target_size_bytes * 0.9:
                        return best_result
                # If this quality setting is already under target, no need to try lower qualities
                break
    
    # If we found a valid result, return it
    if best_result:
        return best_result
    
    # If nothing worked, use minimum settings as last resort
    min_scale = min(0.02, scale_to_fit)
    min_width = max(20, min(int(width * min_scale), max_width))
    min_height = max(20, min(int(height * min_scale), max_height))
    resized = img.resize((min_width, min_height), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    resized.save(buffer, format='JPEG', quality=5, optimize=True)
    return buffer.getvalue()

def main():
    # Set up paths
    wiki_links_path = Path("../data/wiki_links.json")
    input_dir = Path("../data/images")
    output_dir = Path("../data/images_test")
    
    # Clear output directory if it exists, then create it
    if output_dir.exists():
        shutil.rmtree(output_dir)
        print(f"Cleared existing {output_dir} directory")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load wiki_links.json
    with open(wiki_links_path, 'r') as f:
        wiki_data = json.load(f)
    
    print(f"Loaded {len(wiki_data)} entries from wiki_links.json")
    
    # Process each entry
    successful = 0
    failed = 0
    skipped = 0
    
    for i, entry in enumerate(wiki_data, 1):
        flickr_id = entry.get('flickr_id')
        hdl_url = entry.get('hdl_url')
        
        # Skip if no hdl_url or flickr_id
        if not hdl_url or not flickr_id:
            skipped += 1
            continue
        
        # Extract filename from hdl_url (last part after last /)
        hdl_filename = hdl_url.split('/')[-1] + '.jpg'
        source_path = input_dir / hdl_filename
        
        # Check if source file exists
        if not source_path.exists():
            print(f"Warning: Source file not found: {source_path}")
            failed += 1
            continue
        
        try:
            print(f"Processing {i}/{len(wiki_data)}: {hdl_filename} -> {flickr_id}.jpg", end="")
            
            # Get original size
            original_size = os.path.getsize(source_path)
            
            # Resize image
            resized_data = resize_image_to_target_size(source_path, target_size_kb=3)
            
            # Save resized image with flickr_id as name
            output_path = output_dir / f"{flickr_id}.jpg"
            
            with open(output_path, 'wb') as f:
                f.write(resized_data)
            
            new_size = len(resized_data)
            print(f" - Done! ({original_size:,} bytes -> {new_size:,} bytes, "
                  f"{new_size/1024:.1f}KB)")
            successful += 1
            
        except Exception as e:
            print(f" - Failed: {e}")
            failed += 1
    
    print(f"\nComplete!")
    print(f"  Successfully processed: {successful} images")
    print(f"  Failed: {failed} images")
    print(f"  Skipped (no hdl_url): {skipped} entries")
    print(f"  Resized images saved to: {output_dir}")
    
    # Show size distribution
    if successful > 0:
        sizes = []
        for file in output_dir.glob("*.jpg"):
            sizes.append(os.path.getsize(file) / 1024)
        
        if sizes:
            print(f"\nSize statistics:")
            print(f"  Min: {min(sizes):.1f} KB")
            print(f"  Max: {max(sizes):.1f} KB")
            print(f"  Avg: {sum(sizes)/len(sizes):.1f} KB")

if __name__ == "__main__":
    main()