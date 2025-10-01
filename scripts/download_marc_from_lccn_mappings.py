#!/usr/bin/env python3
"""
Download MARC XML files based on LCCN mappings from hdl_to_lccn.json and hdl_to_lccn_part2.json
"""

import json
import requests
from pathlib import Path
import time
import re
from typing import Set, Optional

def load_json(file_path: Path) -> dict:
    """Load JSON data from a file."""
    if not file_path.exists():
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)

def extract_lccn_from_url(url: str) -> Optional[str]:
    """Extract LCCN from a loc.gov item URL."""
    # Pattern: https://www.loc.gov/item/2023868470/
    match = re.search(r'/item/(\d+)/?', url)
    if match:
        return match.group(1)
    return None

def collect_lccns(hdl_to_lccn_data: dict, hdl_to_lccn_part2_data: dict) -> Set[str]:
    """Collect all unique LCCNs from both data sources."""
    lccns = set()
    
    # Process hdl_to_lccn.json format
    for hdl_url, data in hdl_to_lccn_data.items():
        if isinstance(data, dict) and 'lccn' in data:
            lccn = data['lccn']
            if lccn:
                lccns.add(lccn)
    
    # Process hdl_to_lccn_part2.json format (HDL URL -> LOC URL)
    for hdl_url, loc_url in hdl_to_lccn_part2_data.items():
        if isinstance(loc_url, str):
            lccn = extract_lccn_from_url(loc_url)
            if lccn:
                lccns.add(lccn)
    
    return lccns

def download_marc_xml(lccn: str, output_dir: Path) -> bool:
    """
    Download MARC XML for a given LCCN.
    Returns True if successful, False otherwise.
    """
    marc_url = f"https://lccn.loc.gov/{lccn}/marcxml"
    
    try:
        response = requests.get(marc_url, timeout=30)
        if response.status_code == 200:
            # Save the MARC XML
            output_file = output_dir / f"{lccn}.xml"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            return True
        else:
            print(f"  Failed to download: HTTP {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"  Error downloading: {e}")
        return False

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    hdl_to_lccn_file = base_dir / 'data' / 'hdl_to_lccn.json'
    hdl_to_lccn_part2_file = base_dir / 'data' / 'hdl_to_lccn_part2.json'
    output_dir = base_dir / 'data' / 'marc_files_from_search'
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading mapping files...")
    
    # Load both JSON files
    hdl_to_lccn_data = load_json(hdl_to_lccn_file)
    print(f"Loaded {len(hdl_to_lccn_data)} entries from hdl_to_lccn.json")
    
    hdl_to_lccn_part2_data = load_json(hdl_to_lccn_part2_file)
    print(f"Loaded {len(hdl_to_lccn_part2_data)} entries from hdl_to_lccn_part2.json")
    
    # Collect all unique LCCNs
    print("\nCollecting LCCNs...")
    all_lccns = collect_lccns(hdl_to_lccn_data, hdl_to_lccn_part2_data)
    print(f"Found {len(all_lccns)} unique LCCNs")
    
    # Check which MARC files already exist
    existing_files = set()
    for xml_file in output_dir.glob("*.xml"):
        lccn = xml_file.stem  # filename without extension
        existing_files.add(lccn)
    
    # Filter out already downloaded LCCNs
    lccns_to_download = all_lccns - existing_files
    
    if existing_files:
        print(f"\nSkipping {len(existing_files)} already downloaded MARC files")
    
    if not lccns_to_download:
        print("\nAll MARC files have already been downloaded!")
        return
    
    print(f"\nDownloading {len(lccns_to_download)} MARC XML files...")
    print("Press Ctrl+C to stop at any time.\n")
    
    # Download MARC files
    downloaded = 0
    failed = 0
    
    try:
        for i, lccn in enumerate(sorted(lccns_to_download), 1):
            print(f"[{i}/{len(lccns_to_download)}] Downloading LCCN {lccn}...")
            
            if download_marc_xml(lccn, output_dir):
                downloaded += 1
                print(f"  ✓ Saved to {lccn}.xml")
            else:
                failed += 1
            
            # Pause between requests (except for the last one)
            if i < len(lccns_to_download):
                time.sleep(2)
    
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    
    # Print summary
    print(f"\n=== Summary ===")
    print(f"Total unique LCCNs found: {len(all_lccns)}")
    print(f"Already downloaded: {len(existing_files)}")
    print(f"Downloaded this session: {downloaded}")
    print(f"Failed downloads: {failed}")
    print(f"Remaining to download: {len(lccns_to_download) - downloaded - failed}")
    
    if downloaded > 0:
        print(f"\nMARC files saved to: {output_dir}")

if __name__ == "__main__":
    main()