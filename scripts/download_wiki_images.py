#!/usr/bin/env python3

import json
import os
import re
import shutil
import time
import requests
from pathlib import Path

def hdl_to_asset_url(hdl_url):
    """
    Convert HDL URL to asset URL
    http://hdl.loc.gov/loc.pnp/ggbain.22075 -> https://tile.loc.gov/storage-services/service/pnp/ggbain/22000/22075r.jpg
    http://hdl.loc.gov/loc.pnp/mrg.02926 -> https://tile.loc.gov/storage-services/service/pnp/mrg/02900/02926r.jpg
    https://hdl.loc.gov/loc.pnp/highsm.65452 -> https://tile.loc.gov/storage-services/service/pnp/highsm/65400/65452r.jpg
    http://hdl.loc.gov/loc.pnp/stereo.1s22874 -> https://tile.loc.gov/storage-services/service/pnp/stereo/1s20000/1s22000/1s22800/1s22874r.jpg
    http://hdl.loc.gov/loc.pnp/fsa.8a10836 -> https://tile.loc.gov/storage-services/service/pnp/fsa/8a10000/8a10800/8a10836r.jpg
    http://hdl.loc.gov/loc.pnp/fsa.8a32856 -> https://tile.loc.gov/storage-services/service/pnp/fsa/8a32000/8a32800/8a32856r.jpg
    http://hdl.loc.gov/loc.pnp/fsac.1a34376 -> https://tile.loc.gov/storage-services/service/pnp/fsac/1a34000/1a34300/1a34376r.jpg
    http://hdl.loc.gov/loc.pnp/cph.3b48920 -> https://tile.loc.gov/storage-services/service/pnp/cph/3b40000/3b48000/3b48900/3b48920r.jpg
    http://hdl.loc.gov/loc.pnp/pan.6a06678 -> https://tile.loc.gov/storage-services/service/pnp/pan/6a06000/6a06600/6a06678r.jpg
    http://hdl.loc.gov/loc.pnp/cai.2a11699 -> https://tile.loc.gov/storage-services/service/pnp/cai/2a11000/2a11600/2a11699r.jpg
    http://hdl.loc.gov/loc.music/gottlieb.05751 -> https://tile.loc.gov/image-services/iiif/public:music:musgottlieb-05751:0001/full/pct:6.25/0/default.jpg
    """
    if not hdl_url:
        return None
    
    # Special handling for gottlieb music collection
    # Pattern: http(s)://hdl.loc.gov/loc.music/gottlieb.ID
    match_gottlieb = re.match(r'https?://hdl\.loc\.gov/loc\.music/gottlieb\.(\d+)', hdl_url)
    if match_gottlieb:
        image_id = match_gottlieb.group(1)
        # Convert to IIIF URL format
        # gottlieb.05751 -> https://tile.loc.gov/image-services/iiif/public:music:musgottlieb-05751:0001/full/pct:6.25/0/default.jpg
        # gottlieb.16131 -> https://tile.loc.gov/image-services/iiif/public:music:musgottlieb-16131-001:0001/full/pct:6.25/0/default.jpg
        
        # First try without -001 suffix
        asset_url = f"https://tile.loc.gov/image-services/iiif/public:music:musgottlieb-{image_id}:0001/full/pct:6.25/0/default.jpg"
        return asset_url
    
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
            # 1s22874 -> 1s20000/1s22000/1s22800/1s22874r.jpg
            folder1_num = (id_num // 10000) * 10000  # 20000
            folder2_num = (id_num // 1000) * 1000    # 22000
            folder3_num = (id_num // 100) * 100      # 22800
            
            folder1 = f"1s{folder1_num:05d}"
            folder2 = f"1s{folder2_num:05d}"
            folder3 = f"1s{folder3_num:05d}"
            
            asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{folder3}/{image_id}r.jpg"
            return asset_url
    
    # Special handling for FSA collection with alphanumeric IDs
    elif collection == 'fsa' and image_id.startswith('8'):
        # FSA IDs have two patterns:
        # Pattern 1: 8a10836 -> 8a10000/8a10800/8a10836r.jpg (7 chars)
        # Pattern 2: 8a32856 -> 8a32000/8a32800/8a32856r.jpg (7 chars)
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
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{image_id}r.jpg"
                return asset_url
    
    # Special handling for FSAC collection with alphanumeric IDs
    elif collection == 'fsac' and image_id.startswith('1'):
        # FSAC IDs like 1a34376 -> 1a34000/1a34300/1a34376r.jpg
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
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{image_id}r.jpg"
                return asset_url
    
    # Special handling for CPH collection with alphanumeric IDs
    elif collection == 'cph' and image_id.startswith('3'):
        # CPH IDs like 3b48920 -> 3b40000/3b48000/3b48900/3b48920r.jpg
        # or 3c18028 -> 3c10000/3c18000/3c18000/3c18028r.jpg
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
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{folder3}/{image_id}r.jpg"
                return asset_url
    
    # Special handling for PAN collection with alphanumeric IDs
    elif collection == 'pan' and image_id.startswith('6'):
        # PAN IDs like 6a06678 -> 6a06000/6a06600/6a06678r.jpg
        # or 6a32762 -> 6a32000/6a32700/6a32762r.jpg
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
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{image_id}r.jpg"
                return asset_url
    
    # Special handling for CAI collection with alphanumeric IDs
    elif collection == 'cai' and image_id.startswith('2'):
        # CAI IDs like 2a11699 -> 2a11000/2a11600/2a11699r.jpg
        # Extract prefix and numeric parts
        if len(image_id) >= 7:  # e.g., 2a11699
            prefix = image_id[:2]  # '2a'
            numeric_part = image_id[2:]  # '11699'
            if numeric_part.isdigit():
                id_num = int(numeric_part)
                
                # Create two-level folder structure
                folder1_num = (id_num // 1000) * 1000  # 11000
                folder2_num = (id_num // 100) * 100    # 11600
                
                folder1 = f"{prefix}{folder1_num:05d}"
                folder2 = f"{prefix}{folder2_num:05d}"
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{image_id}r.jpg"
                return asset_url
    
    # Special handling for DET collection with alphanumeric IDs
    elif collection == 'det' and image_id.startswith('4'):
        # DET IDs like 4a21672 -> 4a20000/4a21000/4a21600/4a21672r.jpg
        # Extract prefix and numeric parts
        if len(image_id) >= 7:  # e.g., 4a21672
            prefix = image_id[:2]  # '4a'
            numeric_part = image_id[2:]  # '21672'
            if numeric_part.isdigit():
                id_num = int(numeric_part)
                
                # Create three-level folder structure
                folder1_num = (id_num // 10000) * 10000  # 20000
                folder2_num = (id_num // 1000) * 1000    # 21000
                folder3_num = (id_num // 100) * 100      # 21600
                
                folder1 = f"{prefix}{folder1_num:05d}"
                folder2 = f"{prefix}{folder2_num:05d}"
                folder3 = f"{prefix}{folder3_num:05d}"
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{folder3}/{image_id}r.jpg"
                return asset_url
    
    # Special handling for BBC collection with mixed alphanumeric IDs
    elif collection == 'bbc':
        # BBC IDs like 1368f -> 1300/1360/1368fr.jpg
        # Extract numeric part and suffix
        # Handle IDs that end with a letter (like 1368f)
        match = re.match(r'^(\d+)([a-z]?)$', image_id)
        if match:
            numeric_part = match.group(1)
            suffix = match.group(2)  # Will be empty string if no letter
            
            if numeric_part.isdigit():
                id_num = int(numeric_part)
                
                # Create two-level folder structure
                folder1_num = (id_num // 100) * 100   # 1300
                folder2_num = (id_num // 10) * 10     # 1360
                
                # Format folders based on the ID length
                if len(numeric_part) <= 4:
                    folder1 = f"{folder1_num:04d}"
                    folder2 = f"{folder2_num:04d}"
                else:
                    folder1 = f"{folder1_num:05d}"
                    folder2 = f"{folder2_num:05d}"
                
                # Include the suffix in the filename if present
                filename = f"{numeric_part}{suffix}r.jpg"
                
                asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder1}/{folder2}/{filename}"
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
        asset_url = f"https://tile.loc.gov/storage-services/service/pnp/{collection}/{folder}/{image_id}r.jpg"
        return asset_url
    
    return None

def get_image_filename(hdl_url):
    """
    Extract filename from HDL URL
    http://hdl.loc.gov/loc.pnp/mrg.02926 -> mrg.02926.jpg
    https://hdl.loc.gov/loc.pnp/highsm.65452 -> highsm.65452.jpg
    http://hdl.loc.gov/loc.pnp/stereo.1s22874 -> stereo.1s22874.jpg
    http://hdl.loc.gov/loc.music/gottlieb.05751 -> gottlieb.05751.jpg
    """
    if not hdl_url:
        return None
    
    # Handle music/gottlieb collection
    match_gottlieb = re.match(r'https?://hdl\.loc\.gov/loc\.music/(gottlieb\.\d+)', hdl_url)
    if match_gottlieb:
        return f"{match_gottlieb.group(1)}.jpg"
    
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
            
            # Get file size for reporting
            file_size = len(content)
            
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
    """Download images from Library of Congress based on HDL URLs in wiki_links.json"""
    
    # Paths
    input_file = os.path.join('..', 'data', 'wiki_links.json')
    output_dir = os.path.join('..', 'data', 'images')
    existing_dir = os.path.join('..', 'apps', 'street_view', 'img')
    
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
    
    # Check existing files in both directories
    existing_files_output = set(os.listdir(output_dir)) if os.path.exists(output_dir) else set()
    existing_files_source = set(os.listdir(existing_dir)) if os.path.exists(existing_dir) else set()
    print(f"Found {len(existing_files_output)} existing images in {output_dir}")
    print(f"Found {len(existing_files_source)} existing images in {existing_dir}")
    
    # Statistics
    successful_downloads = 0
    failed_downloads = 0
    skipped_existing = 0
    copied_from_existing = 0
    no_asset_url = 0
    no_asset_url_list = []  # Track URLs that couldn't be converted
    
    # Process each record
    for idx, record in enumerate(records_with_hdl, 1):
        hdl_url = record.get('hdl_url')
        flickr_id = record.get('flickr_id', 'unknown')
        
        print(f"\n[{idx}/{len(records_with_hdl)}] Processing Flickr ID {flickr_id}")
        print(f"  HDL URL: {hdl_url}")
        
        # Get filename
        filename = get_image_filename(hdl_url)
        if not filename:
            print(f"  ❌ Could not extract filename from HDL URL")
            no_asset_url += 1
            no_asset_url_list.append(hdl_url)
            continue
        
        output_filepath = os.path.join(output_dir, filename)
        existing_filepath = os.path.join(existing_dir, filename)
        
        # Check if already in output directory
        if filename in existing_files_output:
            # Verify the existing file exists
            if os.path.exists(output_filepath):
                file_size = os.path.getsize(output_filepath)
                print(f"  ✓ Already in output directory ({file_size / (1024*1024):.2f} MB)")
                skipped_existing += 1
                continue
        
        # Check if exists in street_view/img directory
        if filename in existing_files_source:
            if os.path.exists(existing_filepath):
                file_size = os.path.getsize(existing_filepath)
                print(f"  📋 Found in street_view/img, copying to output directory...")
                shutil.copy2(existing_filepath, output_filepath)
                print(f"  ✅ Copied successfully ({file_size / (1024*1024):.2f} MB)")
                copied_from_existing += 1
                continue
        
        # Convert to asset URL
        asset_url = hdl_to_asset_url(hdl_url)
        if not asset_url:
            print(f"  ❌ Could not convert HDL URL to asset URL")
            no_asset_url += 1
            no_asset_url_list.append(hdl_url)
            continue
        
        print(f"  Asset URL: {asset_url}")
        
        # Download the image
        if download_image(asset_url, output_filepath):
            successful_downloads += 1
            
            # Add a 1-second delay to be respectful to the server
            print(f"  ⏳ Waiting 1 second before next download...")
            time.sleep(1)
        else:
            failed_downloads += 1
            
            # Try alternative URL patterns if the standard one fails
            print(f"  Trying alternative URL patterns...")
            
            # Special handling for gottlieb URLs - try with -001 suffix
            if 'musgottlieb' in asset_url and '-001:' not in asset_url:
                # Try adding -001 suffix before :0001
                # musgottlieb-16131:0001 -> musgottlieb-16131-001:0001
                alt_url = asset_url.replace(':0001', '-001:0001')
                print(f"  Alternative Gottlieb URL: {alt_url}")
                if download_image(alt_url, output_filepath):
                    successful_downloads += 1
                    failed_downloads -= 1  # Correct the count
                    print(f"  ⏳ Waiting 1 second before next download...")
                    time.sleep(1)
                    continue
            
            # Try without 'r' suffix
            alt_url = asset_url.replace('r.jpg', '.jpg')
            print(f"  Alternative URL: {alt_url}")
            if download_image(alt_url, output_filepath):
                successful_downloads += 1
                failed_downloads -= 1  # Correct the count
                print(f"  ⏳ Waiting 1 second before next download...")
                time.sleep(1)
            else:
                # Try with 'v' suffix (variant)
                alt_url = asset_url.replace('r.jpg', 'v.jpg')
                print(f"  Alternative URL: {alt_url}")
                if download_image(alt_url, output_filepath):
                    successful_downloads += 1
                    failed_downloads -= 1  # Correct the count
                    print(f"  ⏳ Waiting 1 second before next download...")
                    time.sleep(1)
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 80)
    print(f"Total records with HDL URLs: {len(records_with_hdl)}")
    print(f"✅ Successfully downloaded: {successful_downloads}")
    print(f"📋 Copied from existing: {copied_from_existing}")
    print(f"✓  Already existed (skipped): {skipped_existing}")
    print(f"❌ Failed to download: {failed_downloads}")
    print(f"⚠️  No valid asset URL: {no_asset_url}")
    print(f"\nTotal images in output directory: {len(os.listdir(output_dir))}")
    
    # List failed downloads for debugging
    if failed_downloads > 0:
        print("\n⚠️ Note: Some downloads failed. You can run the script again to retry.")
        print("The script will skip already downloaded files and only retry failures.")
    
    # List URLs that couldn't be converted
    if no_asset_url_list:
        print(f"\n⚠️ URLs that couldn't be converted to asset URLs ({len(no_asset_url_list)} total):")
        for url in no_asset_url_list:
            print(f"  - {url}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Script interrupted by user")
        print("Progress has been saved. You can resume by running the script again.")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        print("You can resume by running the script again.")