#!/usr/bin/env python3
"""
Search and download MARC records from Library of Congress based on Flickr photo titles.
"""

import json
import os
import hashlib
import requests
import time
from urllib.parse import quote
from typing import Dict, List, Set

# Configuration
DATA_DIR = "../data"
FLICKR_DATA_FILE = os.path.join(DATA_DIR, "flickr_photos_with_metadata.json")
MARC_RESULTS_DIR = os.path.join(DATA_DIR, "loc_marc_search_results")
SUMMARY_FILE = os.path.join(DATA_DIR, "loc_marc_search_summary.json")
LOC_SEARCH_URL = "https://id.loc.gov/resources/works/suggest2/"

def get_title_hash(title: str) -> str:
    """Generate MD5 hash of the title."""
    return hashlib.md5(title.encode('utf-8')).hexdigest()

def clean_title(title: str) -> str:
    """Remove ' (LOC)' from the end of title if it exists."""
    if title.endswith(" (LOC)"):
        return title[:-6]
    return title

def get_existing_hashes() -> Set[str]:
    """Get set of hashes that have already been searched."""
    existing_hashes = set()
    if os.path.exists(MARC_RESULTS_DIR):
        for filename in os.listdir(MARC_RESULTS_DIR):
            if filename.endswith('.json'):
                existing_hashes.add(filename[:-5])  # Remove .json extension
    return existing_hashes

def load_summary() -> Dict:
    """Load existing summary file or create new one."""
    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, 'r') as f:
            return json.load(f)
    return {
        "no_results": [],
        "over_250_results": [],
        "searched_titles": {},
        "stats": {
            "total_searched": 0,
            "with_results": 0,
            "no_results": 0,
            "over_250_results": 0
        }
    }

def save_summary(summary: Dict):
    """Save summary to file."""
    with open(SUMMARY_FILE, 'w') as f:
        json.dump(summary, f, indent=2)

def search_loc(title: str) -> Dict:
    """Search Library of Congress for MARC records."""
    params = {
        'q': title,
        'searchtype': 'keyword',
        'rdftype': 'StillImage',
        'count': 250
    }
    
    try:
        response = requests.get(LOC_SEARCH_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error searching for '{title}': {e}")
        return None

def main():
    # Create directories if they don't exist
    os.makedirs(MARC_RESULTS_DIR, exist_ok=True)
    
    # Load existing data
    existing_hashes = get_existing_hashes()
    summary = load_summary()
    
    # Load Flickr data
    print(f"Loading Flickr data from {FLICKR_DATA_FILE}")
    with open(FLICKR_DATA_FILE, 'r') as f:
        flickr_data = json.load(f)
    
    print(f"Found {len(flickr_data)} Flickr photos")
    print(f"Already searched {len(existing_hashes)} unique titles")
    
    # Track processed titles to avoid duplicates in this run
    processed_titles = set()
    new_searches = 0
    skipped_duplicates = 0
    
    for i, photo in enumerate(flickr_data, 1):
        # Get and clean title
        raw_title = photo.get('title', '')
        if not raw_title:
            continue
        
        cleaned_title = clean_title(raw_title)
        title_hash = get_title_hash(cleaned_title)
        
        # Skip if already processed in this run
        if cleaned_title in processed_titles:
            skipped_duplicates += 1
            continue
        
        processed_titles.add(cleaned_title)
        
        # Skip if already searched in previous runs
        if title_hash in existing_hashes:
            continue
        
        # Perform search
        print(f"[{i}/{len(flickr_data)}] Searching for: {cleaned_title[:80]}...")
        
        result = search_loc(cleaned_title)
        
        if result is None:
            print("  - Search failed, skipping")
            continue
        
        # Save result
        result_file = os.path.join(MARC_RESULTS_DIR, f"{title_hash}.json")
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        new_searches += 1
        
        # Update summary
        hit_count = result.get('count', 0)
        summary['searched_titles'][cleaned_title] = {
            'hash': title_hash,
            'hit_count': hit_count,
            'photo_id': photo.get('id', '')
        }
        
        summary['stats']['total_searched'] += 1
        
        if hit_count == 0:
            summary['no_results'].append({
                'title': cleaned_title,
                'hash': title_hash,
                'photo_id': photo.get('id', '')
            })
            summary['stats']['no_results'] += 1
            print(f"  - No results found")
        elif hit_count >= 250:
            summary['over_250_results'].append({
                'title': cleaned_title,
                'hash': title_hash,
                'photo_id': photo.get('id', ''),
                'count': hit_count
            })
            summary['stats']['over_250_results'] += 1
            print(f"  - Found {hit_count} results (over limit)")
        else:
            summary['stats']['with_results'] += 1
            print(f"  - Found {hit_count} results")
        
        # Save summary after each search
        save_summary(summary)
        
        # Small delay to be polite to the API
        time.sleep(0.5)
    
    # Final summary
    print("\n" + "="*60)
    print("SEARCH COMPLETE")
    print("="*60)
    print(f"New searches performed: {new_searches}")
    print(f"Duplicate titles skipped: {skipped_duplicates}")
    print(f"Total unique titles searched: {summary['stats']['total_searched']}")
    print(f"  - With results: {summary['stats']['with_results']}")
    print(f"  - No results: {summary['stats']['no_results']}")
    print(f"  - Over 250 results: {summary['stats']['over_250_results']}")
    print(f"\nResults saved to: {MARC_RESULTS_DIR}")
    print(f"Summary saved to: {SUMMARY_FILE}")

if __name__ == "__main__":
    main()