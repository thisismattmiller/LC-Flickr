#!/usr/bin/env python3

import os
import random
from pathlib import Path
from PIL import Image
import io

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
    input_dir = Path("../data/images")
    output_dir = Path("../data/images_test")
    
    # Clear output directory if it exists, then create it
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
        print(f"Cleared existing {output_dir} directory")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']:
        image_files.extend(input_dir.glob(ext))
    
    print(f"Found {len(image_files)} images in {input_dir}")
    
    # Select 100 random images
    if len(image_files) > 100:
        selected_images = random.sample(image_files, 100)
    else:
        selected_images = image_files
        print(f"Warning: Only {len(image_files)} images available, using all of them")
    
    print(f"Processing {len(selected_images)} images...")
    
    # Process each image
    successful = 0
    failed = 0
    
    for i, image_path in enumerate(selected_images, 1):
        try:
            print(f"Processing {i}/{len(selected_images)}: {image_path.name}", end="")
            
            # Get original size
            original_size = os.path.getsize(image_path)
            
            # Resize image
            resized_data = resize_image_to_target_size(image_path, target_size_kb=3)
            
            # Save resized image
            output_path = output_dir / f"resized_{image_path.name}"
            if output_path.suffix.lower() not in ['.jpg', '.jpeg']:
                output_path = output_path.with_suffix('.jpg')
            
            with open(output_path, 'wb') as f:
                f.write(resized_data)
            
            new_size = len(resized_data)
            print(f" - Done! ({original_size:,} bytes -> {new_size:,} bytes, "
                  f"{new_size/1024:.1f}KB)")
            successful += 1
            
        except Exception as e:
            print(f" - Failed: {e}")
            failed += 1
    
    print(f"\nComplete! Successfully processed {successful} images, {failed} failed.")
    print(f"Resized images saved to: {output_dir}")
    
    # Show size distribution
    if successful > 0:
        sizes = []
        for file in output_dir.glob("resized_*"):
            sizes.append(os.path.getsize(file) / 1024)
        
        if sizes:
            print(f"\nSize statistics:")
            print(f"  Min: {min(sizes):.1f} KB")
            print(f"  Max: {max(sizes):.1f} KB")
            print(f"  Avg: {sum(sizes)/len(sizes):.1f} KB")

if __name__ == "__main__":
    main()