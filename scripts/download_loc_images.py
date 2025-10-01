#!/usr/bin/env python3

import json
import os
import re
import time
import requests
from pathlib import Path
from urllib.parse import urlparse

def hdl_to_asset_url(hdl_url):
    """
    Convert HDL URL to asset URL
    http://hdl.loc.gov/loc.pnp/ggbain.22075 -> https://tile.loc.gov/storage-services/service/pnp/ggbain/22000/22075v.jpg
    http://hdl.loc.gov/loc.pnp/mrg.02926 -> https://tile.loc.gov/storage-services/service/pnp/mrg/02900/02926v.jpg
    https://hdl.loc.gov/loc.pnp/highsm.65452 -> https://tile.loc.gov/storage-services/service/pnp/highsm/65400/65452v.jpg
    http://hdl.loc.gov/loc.pnp/stereo.1s22874 -> https://tile.loc.gov/storage-services/service/pnp/stereo/1s20000/1s22000/1s22800/1s22874v.jpg
    http://hdl.loc.gov/loc.pnp/fsa.8a10836 -> https://tile.loc.gov/storage-services/service/pnp/fsa/8a10000/8a10800/8a10836v.jpg
    http://hdl.loc.gov/loc.pnp/fsa.8a32856 -> https://tile.loc.gov/storage-services/service/pnp/fsa/8a32000/8a32800/8a32856v.jpg
    http://hdl.loc.gov/loc.pnp/fsac.1a34376 -> https://tile.loc.gov/storage-services/service/pnp/fsac/1a34000/1a34300/1a34376v.jpg
    http://hdl.loc.gov/loc.pnp/cph.3b48920 -> https://tile.loc.gov/storage-services/service/pnp/cph/3b40000/3b48000/3b48900/3b48920v.jpg
    http://hdl.loc.gov/loc.pnp/pan.6a06678 -> https://tile.loc.gov/storage-services/service/pnp/pan/6a06000/6a06600/6a06678v.jpg
    """
    if not hdl_url:
        return None
    
    # Parse the HDL URL to extract collection and ID
    # Pattern: http(s)://hdl.loc.gov/loc.pnp/COLLECTION.ID
    # Special case for collections with prefixes
    match = re.match(r'https?://hdl\.loc\.gov/loc\.pnp/([a-zA-Z]+)\.([a-zA-Z0-9]+)', hdl_url)
    
    if not match:
        return None
    
    collection = match.group(1)
    image_id = match.group(2)
    
    # Special handling for stereo collection with nested folders
    if collection == 'stereo' and image_id.startswith('1s'):
        # Extract the numeric part after '1s'
        numeric_part = image_id[2:]  # Remove '1s' prefix
        if numeric_part.isdigit():
            id_num = int(numeric_part)
            
            # Create nested folder structure
            # 1s22874 -> 1s20000/1s22000/1s22800/1s22874v.jpg
            folder1_num = (id_num // 10000) * 10000  # 20000
            folder2_num = (id_num // 1000) * 1000    # 22000
            folder3_num = (id_num // 100) * 100      # 22800
            
            folder1 = f"1s{folder1_num:05d}"
            folder2 = f"1s{folder2_num:05d}"
            folder3 = f"1s{folder3_num:05d}"
            
            asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{folder3}/{image_id}v.jpg"
            return asset_url
    
    # Special handling for FSA collection with alphanumeric IDs
    elif collection == 'fsa' and image_id.startswith('8'):
        # FSA IDs have two patterns:
        # Pattern 1: 8a10836 -> 8a10000/8a10800/8a10836v.jpg (7 chars)
        # Pattern 2: 8a32856 -> 8a32000/8a32800/8a32856v.jpg (7 chars)
        # Extract prefix and numeric parts
        if len(image_id) >= 7:  # e.g., 8a10836, 8a32856
            prefix = image_id[:2]  # '8a'
            numeric_part = image_id[2:]  # '10836' or '32856'
            if numeric_part.isdigit():
                id_num = int(numeric_part)
                
                # Create two-level folder structure
                folder1_num = (id_num // 1000) * 1000  # 10000 or 32000
                folder2_num = (id_num // 100) * 100    # 10800 or 32800
                
                folder1 = f"{prefix}{folder1_num:05d}"
                folder2 = f"{prefix}{folder2_num:05d}"
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{image_id}v.jpg"
                return asset_url
    
    # Special handling for FSAC collection with alphanumeric IDs
    elif collection == 'fsac' and image_id.startswith('1'):
        # FSAC IDs like 1a34376 -> 1a34000/1a34300/1a34376v.jpg
        # Extract prefix and numeric parts
        if len(image_id) >= 7:  # e.g., 1a34376
            prefix = image_id[:2]  # '1a'
            numeric_part = image_id[2:]  # '34376'
            if numeric_part.isdigit():
                id_num = int(numeric_part)
                
                # Create two-level folder structure
                folder1_num = (id_num // 1000) * 1000  # 34000
                folder2_num = (id_num // 100) * 100    # 34300
                
                folder1 = f"{prefix}{folder1_num:05d}"
                folder2 = f"{prefix}{folder2_num:05d}"
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{image_id}v.jpg"
                return asset_url
    
    # Special handling for CPH collection with alphanumeric IDs
    elif collection == 'cph' and image_id.startswith('3'):
        # CPH IDs like 3b48920 -> 3b40000/3b48000/3b48900/3b48920v.jpg
        # or 3c18028 -> 3c10000/3c18000/3c18000/3c18028v.jpg
        # Extract prefix and numeric parts
        if len(image_id) >= 7:  # e.g., 3b48920, 3c18028
            prefix = image_id[:2]  # '3b' or '3c'
            numeric_part = image_id[2:]  # '48920' or '18028'
            if numeric_part.isdigit():
                id_num = int(numeric_part)
                
                # Create three-level folder structure
                folder1_num = (id_num // 10000) * 10000  # 40000 or 10000
                folder2_num = (id_num // 1000) * 1000    # 48000 or 18000
                folder3_num = (id_num // 100) * 100      # 48900 or 18000
                
                folder1 = f"{prefix}{folder1_num:05d}"
                folder2 = f"{prefix}{folder2_num:05d}"
                folder3 = f"{prefix}{folder3_num:05d}"
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{folder3}/{image_id}v.jpg"
                return asset_url
    
    # Special handling for PAN collection with alphanumeric IDs
    elif collection == 'pan' and image_id.startswith('6'):
        # PAN IDs like 6a06678 -> 6a06000/6a06600/6a06678v.jpg
        # or 6a32762 -> 6a32000/6a32700/6a32762v.jpg
        # Extract prefix and numeric parts
        if len(image_id) >= 7:  # e.g., 6a06678, 6a32762
            prefix = image_id[:2]  # '6a'
            numeric_part = image_id[2:]  # '06678' or '32762'
            if numeric_part.isdigit():
                id_num = int(numeric_part)
                
                # Create two-level folder structure
                folder1_num = (id_num // 1000) * 1000  # 06000 or 32000
                folder2_num = (id_num // 100) * 100    # 06600 or 32700
                
                folder1 = f"{prefix}{folder1_num:05d}"
                folder2 = f"{prefix}{folder2_num:05d}"
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{image_id}v.jpg"
                return asset_url
    
    # For numeric IDs, use the standard folder structure
    if image_id.isdigit():
        id_num = int(image_id)
        folder_num = (id_num // 100) * 100
        
        # Format folder with appropriate padding based on the ID length
        if len(image_id) <= 5:
            folder = f"{folder_num:05d}"  # Format with 5 digits
        else:
            folder = f"{folder_num:06d}"  # Format with 6 digits for larger IDs
        
        # Construct the asset URL
        asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder}/{image_id}v.jpg"
        return asset_url
    
    return None

def get_image_filename(hdl_url):
    """
    Extract filename from HDL URL
    http://hdl.loc.gov/loc.pnp/mrg.02926 -> mrg.02926.jpg
    https://hdl.loc.gov/loc.pnp/highsm.65452 -> highsm.65452.jpg
    http://hdl.loc.gov/loc.pnp/stereo.1s22874 -> stereo.1s22874.jpg
    """
    if not hdl_url:
        return None
    
    # Updated pattern to handle alphanumeric IDs (like 1s22874)
    match = re.match(r'https?://hdl\.loc\.gov/loc\.pnp/([a-zA-Z]+\.[a-zA-Z0-9]+)', hdl_url)
    if match:
        return f"{match.group(1)}.jpg"
    
    return None

def download_image(url, filepath, max_retries=3, timeout=30):
    """
    Download image with retry logic and validation
    """
    for attempt in range(max_retries):
        try:
            print(f"    Attempt {attempt + 1}/{max_retries}: Downloading...")
            
            # Make request with timeout
            headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"}
            response = requests.get(url, timeout=timeout, stream=True, headers=headers)

            # Check status code
            if response.status_code == 404:
                print(f"    ❌ Image not found (404)")
                return False
            elif response.status_code != 200:
                print(f"    ⚠️  HTTP {response.status_code}, retrying...")
                time.sleep(2 * (attempt + 1))  # Exponential backoff
                continue
            
            # Download the content
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk
            
            # Validate file size (should be at least 100KB for a decent image)
            file_size = len(content)
            if file_size < 50 * 1024:  # 100KB minimum
                print(f"    ⚠️  File too small ({file_size} bytes), retrying...")
                time.sleep(2 * (attempt + 1))
                continue
            
            # Check if it's actually an image (JPEG magic bytes: FF D8 FF)
            if not content.startswith(b'\xff\xd8\xff'):
                print(f"    ⚠️  Not a valid JPEG file, retrying...")
                time.sleep(2 * (attempt + 1))
                continue
            
            # Save the file
            with open(filepath, 'wb') as f:
                f.write(content)
            
            file_size_mb = file_size / (1024 * 1024)
            print(f"    ✅ Downloaded successfully ({file_size_mb:.2f} MB)")
            return True
            
        except requests.exceptions.Timeout:
            print(f"    ⚠️  Timeout error, retrying...")
            time.sleep(3 * (attempt + 1))
        except requests.exceptions.ConnectionError:
            print(f"    ⚠️  Connection error, retrying...")
            time.sleep(5 * (attempt + 1))
        except Exception as e:
            print(f"    ⚠️  Error: {e}, retrying...")
            time.sleep(2 * (attempt + 1))
    
    print(f"    ❌ Failed after {max_retries} attempts")
    return False

def main():
    """Download images from Library of Congress based on HDL URLs"""
    
    # Paths
    input_file = os.path.join('..', 'data', 'mapping_data_with_locations.json')
    output_dir = os.path.join('..', 'apps', 'street_view', 'img')
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the JSON data
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} records")
    
    # Filter records with HDL URLs
    records_with_hdl = [r for r in data if r.get('hdl_url')]
    print(f"Found {len(records_with_hdl)} records with HDL URLs")
    
    # Check existing files for resume capability
    existing_files = set(os.listdir(output_dir))
    print(f"Found {len(existing_files)} existing images in {output_dir}")
    
    # Statistics
    successful_downloads = 0
    failed_downloads = 0
    skipped_existing = 0
    no_asset_url = 0
    
    # Process each record
    for idx, record in enumerate(records_with_hdl, 1):
        hdl_url = record.get('hdl_url')
        photo_id = record.get('photo_id', 'unknown')
        title = record.get('title', 'No title')[:50]
        
        print(f"\n[{idx}/{len(records_with_hdl)}] Processing {photo_id}: {title}...")
        print(f"  HDL URL: {hdl_url}")
        
        # Get filename
        filename = get_image_filename(hdl_url)
        if not filename:
            print(f"  ❌ Could not extract filename from HDL URL")
            no_asset_url += 1
            continue
        
        filepath = os.path.join(output_dir, filename)
        
        # Check if already downloaded
        if filename in existing_files:
            # Verify the existing file is valid
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                if file_size >= 50 * 1024:  # At least 50KB
                    print(f"  ✓ Already downloaded ({file_size / (1024*1024):.2f} MB)")
                    skipped_existing += 1
                    continue
                else:
                    print(f"  ⚠️  Existing file too small ({file_size} bytes), re-downloading...")
        
        # Convert to asset URL
        asset_url = hdl_to_asset_url(hdl_url)
        if not asset_url:
            print(f"  ❌ Could not convert HDL URL to asset URL")
            no_asset_url += 1
            continue
        
        print(f"  Asset URL: {asset_url}")
        
        # Download the image
        if download_image(asset_url, filepath):
            successful_downloads += 1
            
            # Add a 5-second delay to be respectful to the server
            print(f"  ⏳ Waiting 5 seconds before next download...")
            time.sleep(1)
        else:
            failed_downloads += 1
            
            # Try alternative URL patterns if the standard one fails
            print(f"  Trying alternative URL patterns...")
            
            # Try without 'v' suffix
            alt_url = asset_url.replace('v.jpg', '.jpg')
            print(f"  Alternative URL: {alt_url}")
            if download_image(alt_url, filepath):
                successful_downloads += 1
                failed_downloads -= 1  # Correct the count
                print(f"  ⏳ Waiting 5 seconds before next download...")
                time.sleep(1)
            else:
                # Try with 'r' suffix (reference/thumbnail)
                alt_url = asset_url.replace('v.jpg', 'r.jpg')
                print(f"  Alternative URL: {alt_url}")
                if download_image(alt_url, filepath):
                    successful_downloads += 1
                    failed_downloads -= 1  # Correct the count
                    print(f"  ⏳ Waiting 5 seconds before next download...")
                    time.sleep(1)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"Total records with HDL URLs: {len(records_with_hdl)}")
    print(f"✅ Successfully downloaded: {successful_downloads}")
    print(f"✓  Already existed (skipped): {skipped_existing}")
    print(f"❌ Failed to download: {failed_downloads}")
    print(f"⚠️  No valid asset URL: {no_asset_url}")
    print(f"\nTotal images in directory: {len(os.listdir(output_dir))}")
    
    # List failed downloads for debugging
    if failed_downloads > 0:
        print("\n⚠️ Note: Some downloads failed. You can run the script again to retry.")
        print("The script will skip already downloaded files and only retry failures.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrupted by user")
        print("Progress has been saved. You can resume by running the script again.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        print("You can resume by running the script again.")