#!/usr/bin/env python3
"""
Download MARC XML files from Library of Congress based on title search results.
"""

import json
import os
import requests
import time
from typing import List, Dict, Optional

# Configuration
SEARCH_RESULTS_DIR = "../data/loc_marc_search_results"
MARC_OUTPUT_DIR = "../data/marc_files_from_search"
LOC_MARC_URL_TEMPLATE = "https://id.loc.gov/data/bibs/{}.marcxml.xml"
CACHE_FILE_404 = "../data/marc_404_cache.json"

def extract_bib_id_from_uri(uri: str) -> Optional[str]:
    """Extract bib ID from URI like http://id.loc.gov/resources/works/19676406."""
    try:
        # Get the last part of the URI path
        bib_id = uri.rstrip('/').split('/')[-1]
        # Verify it's numeric
        if bib_id.isdigit():
            return bib_id
        return None
    except Exception as e:
        print(f"    Error extracting bib ID from {uri}: {e}")
        return None

def load_404_cache() -> set:
    """Load the set of bib IDs that returned 404."""
    if os.path.exists(CACHE_FILE_404):
        try:
            with open(CACHE_FILE_404, 'r') as f:
                data = json.load(f)
                return set(data.get('bib_ids_404', []))
        except Exception as e:
            print(f"Warning: Could not load 404 cache: {e}")
    return set()

def save_404_cache(bib_ids_404: set):
    """Save the set of bib IDs that returned 404."""
    try:
        with open(CACHE_FILE_404, 'w') as f:
            json.dump({'bib_ids_404': list(bib_ids_404), 'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')}, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save 404 cache: {e}")

def download_marc_xml(bib_id: str, cache_404: set) -> tuple[bool, bool]:
    """Download MARC XML for a given bib ID. Returns (success, is_404)."""
    url = LOC_MARC_URL_TEMPLATE.format(bib_id)
    output_file = os.path.join(MARC_OUTPUT_DIR, f"{bib_id}.xml")
    
    # Check if already downloaded
    if os.path.exists(output_file):
        print(f"    ⏭ Already downloaded: {bib_id}.xml")
        return False, False
    
    # Check if in 404 cache
    if bib_id in cache_404:
        print(f"    ⏭ Skipping (cached 404): {bib_id}")
        return False, True
    
    try:
        print(f"    Downloading: {url}")
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            # Save the XML content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"    ✓ Saved: {bib_id}.xml")
            return True, False
        elif response.status_code == 404:
            print(f"    ✗ 404 Not Found: {bib_id}")
            return False, True
        else:
            print(f"    ✗ Failed to download (HTTP {response.status_code}): {bib_id}")
            return False, False
            
    except requests.RequestException as e:
        print(f"    ✗ Error downloading {bib_id}: {e}")
        return False, False

def process_search_result_file(filepath: str) -> List[str]:
    """Process a single search result JSON file and extract bib IDs."""
    bib_ids = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract hits
        hits = data.get('hits', [])
        
        for hit in hits:
            uri = hit.get('uri', '')
            if uri:
                bib_id = extract_bib_id_from_uri(uri)
                if bib_id:
                    bib_ids.append(bib_id)
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Error parsing JSON file {filepath}: {e}")
    except Exception as e:
        print(f"  ✗ Error processing file {filepath}: {e}")
    
    return bib_ids

def get_already_downloaded() -> set:
    """Get set of bib IDs that have already been downloaded."""
    downloaded = set()
    if os.path.exists(MARC_OUTPUT_DIR):
        for filename in os.listdir(MARC_OUTPUT_DIR):
            if filename.endswith('.xml'):
                # Remove .xml extension to get bib ID
                bib_id = filename[:-4]
                downloaded.add(bib_id)
    return downloaded

def main():
    # Create output directory if it doesn't exist
    os.makedirs(MARC_OUTPUT_DIR, exist_ok=True)
    
    # Load 404 cache
    cache_404 = load_404_cache()
    print(f"Loaded 404 cache with {len(cache_404)} entries\n")
    
    # Get already downloaded files
    already_downloaded = get_already_downloaded()
    print(f"Found {len(already_downloaded)} already downloaded MARC files\n")
    
    # Check if search results directory exists
    if not os.path.exists(SEARCH_RESULTS_DIR):
        print(f"Error: Search results directory not found: {SEARCH_RESULTS_DIR}")
        return
    
    # Get all JSON files in search results directory
    json_files = [f for f in os.listdir(SEARCH_RESULTS_DIR) if f.endswith('.json')]
    print(f"Found {len(json_files)} search result files to process\n")
    
    # Track statistics
    total_bib_ids_found = 0
    total_downloaded = 0
    total_skipped = 0
    total_failed = 0
    total_404 = 0
    all_bib_ids = set()
    new_404s = set()
    
    # Process each search result file
    total_counter = 0

    for i, filename in enumerate(json_files, 1):
        total_counter += 1
        if total_counter < 25000:
            print(total_counter)
            continue

        filepath = os.path.join(SEARCH_RESULTS_DIR, filename)
        print(f"[{i}/{len(json_files)}] Processing: {filename}")
        
        # Extract bib IDs from this file
        bib_ids = process_search_result_file(filepath)
        
        if not bib_ids:
            print(f"  No bib IDs found in this file")
            continue
        
        print(f"  Found {len(bib_ids)} bib ID(s)")
        total_bib_ids_found += len(bib_ids)
        
        # Track success and 404s for this specific file
        file_successes = 0
        file_404s_after_success = 0
        
        # Download MARC XML for each bib ID
        for idx, bib_id in enumerate(bib_ids):

            
            if bib_id in all_bib_ids:
                print(f"    ⏭ Duplicate bib ID: {bib_id}")
                continue
            
            all_bib_ids.add(bib_id)
            
            if bib_id in already_downloaded:
                total_skipped += 1
                file_successes += 1  # Count as success since it was downloaded before
                continue
            
            # If we've had success with this file and now getting 404s, skip the rest
            if file_successes > 0 and file_404s_after_success >= 2:
                remaining = len(bib_ids) - idx
                print(f"    ⏭ Skipping {remaining} remaining IDs (got {file_404s_after_success} 404s after successful downloads)")
                # Mark remaining as skipped
                total_skipped += remaining - 1  # -1 because current one is already counted as 404
                break
            
            # Download the MARC XML
            success, is_404 = download_marc_xml(bib_id, cache_404)
            
            if success:
                total_downloaded += 1
                file_successes += 1
                file_404s_after_success = 0  # Reset 404 counter on success
                # Small delay to be polite to the server
                time.sleep(0.5)
            elif is_404:
                total_404 += 1
                if bib_id not in cache_404:
                    new_404s.add(bib_id)
                # Track 404s after success
                if file_successes > 0:
                    file_404s_after_success += 1
            else:
                # If already exists, count as skipped, otherwise as failed
                if os.path.exists(os.path.join(MARC_OUTPUT_DIR, f"{bib_id}.xml")):
                    total_skipped += 1
                    file_successes += 1
                else:
                    total_failed += 1
    
    # Update 404 cache with new entries
    if new_404s:
        cache_404.update(new_404s)
        save_404_cache(cache_404)
        print(f"\nAdded {len(new_404s)} new entries to 404 cache")
    
    # Print summary
    print("\n" + "="*60)
    print("DOWNLOAD COMPLETE")
    print("="*60)
    print(f"Total search result files processed: {len(json_files)}")
    print(f"Total unique bib IDs found: {len(all_bib_ids)}")
    print(f"Newly downloaded: {total_downloaded}")
    print(f"Already downloaded (skipped): {total_skipped}")
    print(f"404 Not Found (skipped): {total_404}")
    print(f"Failed downloads: {total_failed}")
    print(f"\nMARC XML files saved to: {MARC_OUTPUT_DIR}")
    print(f"Total MARC files in directory: {len(get_already_downloaded())}")
    print(f"Total 404s in cache: {len(cache_404)}")

if __name__ == "__main__":
    main()