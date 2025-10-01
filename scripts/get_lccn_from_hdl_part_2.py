#!/usr/bin/env python3
"""
Process unmapped HDL URLs to capture their redirect locations.
Supports incremental processing and can be stopped/restarted.
"""

import json
import requests
from pathlib import Path
import time
from typing import Dict, List
import signal
import sys

def load_json(file_path: Path) -> dict:
    """Load JSON data from a file."""
    if not file_path.exists():
        return {}
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data: dict, file_path: Path) -> None:
    """Save data to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def get_redirect_url(hdl_url: str) -> str:
    """
    Get the redirect URL from an HDL URL without following the redirect.
    Returns the Location header value or empty string if failed.
    """
    # Convert to HTTPS
    https_url = hdl_url.replace('http://', 'https://')
    
    try:
        # Make request without following redirects
        response = requests.get(https_url, allow_redirects=False, timeout=10)
        
        # Check if it's a redirect status code (3xx)
        if 300 <= response.status_code < 400:
            location = response.headers.get('Location', '')
            return location
        else:
            print(f"No redirect for {hdl_url}: status {response.status_code}")
            return ''
    except requests.RequestException as e:
        print(f"Error fetching {hdl_url}: {e}")
        return ''

class ProgressTracker:
    """Track and save progress for resumable processing."""
    
    def __init__(self, output_file: Path, progress_file: Path):
        self.output_file = output_file
        self.progress_file = progress_file
        self.hdl_to_redirect = {}
        self.processed_urls = set()
        self.failed_urls = set()
        self.should_exit = False
        
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_interrupt)
        
        # Load existing progress if available
        self.load_progress()
    
    def handle_interrupt(self, signum, frame):
        """Handle Ctrl+C for graceful shutdown."""
        print("\n\nReceived interrupt signal. Saving progress...")
        self.should_exit = True
    
    def load_progress(self):
        """Load existing progress from files."""
        # Load existing output file
        if self.output_file.exists():
            self.hdl_to_redirect = load_json(self.output_file)
            print(f"Loaded {len(self.hdl_to_redirect)} existing mappings from {self.output_file.name}")
        
        # Load progress tracking file
        if self.progress_file.exists():
            progress_data = load_json(self.progress_file)
            self.processed_urls = set(progress_data.get('processed_urls', []))
            self.failed_urls = set(progress_data.get('failed_urls', []))
            print(f"Loaded progress: {len(self.processed_urls)} processed, {len(self.failed_urls)} failed")
    
    def save_progress(self):
        """Save current progress to files."""
        # Save the HDL to redirect mappings
        save_json(self.hdl_to_redirect, self.output_file)
        
        # Save progress tracking
        progress_data = {
            'processed_urls': list(self.processed_urls),
            'failed_urls': list(self.failed_urls),
            'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        save_json(progress_data, self.progress_file)
    
    def add_mapping(self, hdl_url: str, redirect_url: str):
        """Add a successful mapping."""
        self.hdl_to_redirect[hdl_url] = redirect_url
        self.processed_urls.add(hdl_url)
    
    def add_failed(self, hdl_url: str):
        """Mark a URL as failed."""
        self.failed_urls.add(hdl_url)
        self.processed_urls.add(hdl_url)
    
    def is_processed(self, hdl_url: str) -> bool:
        """Check if a URL has already been processed."""
        return hdl_url in self.processed_urls

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    no_match_file = base_dir / 'data' / 'marc_to_flickr_mapping_no_match.json'
    hdl_lccn_file = base_dir / 'data' / 'hdl_to_lccn.json'
    output_file = base_dir / 'data' / 'hdl_to_lccn_part2.json'
    progress_file = base_dir / 'data' / '.hdl_to_lccn_part2_progress.json'
    
    print("Loading data files...")
    
    # Load the no match data
    no_match_data = load_json(no_match_file)
    print(f"Loaded {len(no_match_data)} entries from marc_to_flickr_mapping_no_match.json")
    
    # Load the existing hdl to lccn mappings
    hdl_to_lccn = load_json(hdl_lccn_file)
    print(f"Loaded {len(hdl_to_lccn)} entries from hdl_to_lccn.json")
    
    # Initialize progress tracker
    tracker = ProgressTracker(output_file, progress_file)
    
    # Find HDL URLs that are not in hdl_to_lccn.json
    unmapped_hdls = []
    for hdl_url in no_match_data.keys():
        if hdl_url not in hdl_to_lccn:
            unmapped_hdls.append(hdl_url)
    
    print(f"\nFound {len(unmapped_hdls)} unmapped HDL URLs")
    
    # Filter out already processed URLs
    urls_to_process = [url for url in unmapped_hdls if not tracker.is_processed(url)]
    already_processed = len(unmapped_hdls) - len(urls_to_process)
    
    if already_processed > 0:
        print(f"Skipping {already_processed} already processed URLs")
    
    if not urls_to_process:
        print("\nAll URLs have already been processed!")
        print(f"Total mappings: {len(tracker.hdl_to_redirect)}")
        return
    
    print(f"\nProcessing {len(urls_to_process)} remaining HDL URLs...")
    print("Press Ctrl+C to stop and save progress at any time.\n")
    
    # Process unmapped HDLs to get redirect URLs
    save_interval = 10  # Save every 10 URLs
    
    for i, hdl_url in enumerate(urls_to_process, 1):
        if tracker.should_exit:
            break
            
        print(f"Processing {i}/{len(urls_to_process)} (total: {already_processed + i}/{len(unmapped_hdls)}): {hdl_url}")
        
        redirect_url = get_redirect_url(hdl_url)
        if redirect_url:
            tracker.add_mapping(hdl_url, redirect_url)
            print(f"  -> Redirects to: {redirect_url}")
        else:
            tracker.add_failed(hdl_url)
            print(f"  -> No redirect found")
        
        # Save progress periodically
        if i % save_interval == 0:
            tracker.save_progress()
            print(f"  [Progress saved: {len(tracker.hdl_to_redirect)} mappings]")
        
        # Small delay to be polite to the server
        if i < len(urls_to_process) and not tracker.should_exit:
            time.sleep(0.5)
    
    # Final save
    tracker.save_progress()
    
    # Print summary
    print(f"\n=== Summary ===")
    print(f"Total HDL URLs in no_match file: {len(no_match_data)}")
    print(f"Already mapped in hdl_to_lccn: {len(no_match_data) - len(unmapped_hdls)}")
    print(f"Total to process: {len(unmapped_hdls)}")
    print(f"Previously processed: {already_processed}")
    print(f"Processed this session: {min(len(urls_to_process), len(tracker.processed_urls) - already_processed)}")
    print(f"Successfully captured redirects (total): {len(tracker.hdl_to_redirect)}")
    print(f"Failed to capture redirects (total): {len(tracker.failed_urls)}")
    
    if tracker.should_exit:
        remaining = len(urls_to_process) - (len(tracker.processed_urls) - already_processed)
        print(f"\nStopped early. {remaining} URLs remaining to process.")
        print("Run the script again to continue from where you left off.")
    else:
        print("\nAll URLs processed successfully!")
        print(f"Results saved to {output_file}")
        
        # Clean up progress file when complete
        if progress_file.exists():
            progress_file.unlink()
            print("Progress tracking file cleaned up.")

if __name__ == "__main__":
    main()