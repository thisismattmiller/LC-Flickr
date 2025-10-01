#!/usr/bin/env python3
"""
Expand Wikipedia links to Wikidata QIDs using the Wikipedia API.
Supports resumable processing and handles multiple languages.
"""

import json
import re
import requests
import time
import signal
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from urllib.parse import urlparse, unquote

def load_json(file_path: Path) -> dict:
    """Load JSON data from a file."""
    if not file_path.exists():
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: dict, file_path: Path) -> None:
    """Save data to a JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_qid_from_wikidata_url(url: str) -> Optional[str]:
    """
    Extract QID from a Wikidata URL.
    Example: https://www.wikidata.org/wiki/Q42 -> Q42
    """
    match = re.search(r'/(?:wiki|entity)/(Q\d+)', url)
    if match:
        return match.group(1)
    return None

def parse_wikipedia_url(url: str) -> Optional[Tuple[str, str]]:
    """
    Parse a Wikipedia URL to extract language code and page title.
    Returns (language_code, page_title) or None if not a valid Wikipedia URL.
    """
    parsed = urlparse(url)
    
    # Check if it's a Wikipedia URL
    if 'wikipedia.org' not in parsed.netloc:
        return None
    
    # Extract language code from subdomain
    # Format: lang.wikipedia.org or lang.m.wikipedia.org
    subdomain = parsed.netloc.split('.')[0]
    if subdomain == 'www':
        # Sometimes URLs are www.wikipedia.org/wiki/lang:Title
        return None  # Skip these for now
    lang_code = subdomain
    
    # Extract page title from path
    # Format: /wiki/Page_Title
    path_match = re.match(r'/wiki/(.+)', parsed.path)
    if not path_match:
        return None
    
    page_title = path_match.group(1)
    # Remove fragment if present
    page_title = page_title.split('#')[0]
    # URL decode the title
    page_title = unquote(page_title)
    
    return lang_code, page_title

def get_wikidata_qid_from_wikipedia(lang: str, title: str, session: requests.Session) -> Optional[str]:
    """
    Query Wikipedia API to get the Wikidata QID for a given page.
    """
    # Construct API URL for the specific language Wikipedia
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    
    params = {
        'action': 'query',
        'prop': 'pageprops',
        'ppprop': 'wikibase_item',
        'redirects': '1',
        'format': 'json',
        'titles': title
    }
    
    try:
        response = session.get(api_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract QID from response
        if 'query' in data and 'pages' in data['query']:
            for page_id, page_data in data['query']['pages'].items():
                if 'pageprops' in page_data and 'wikibase_item' in page_data['pageprops']:
                    return page_data['pageprops']['wikibase_item']
        
        return None
        
    except requests.RequestException as e:
        print(f"  Error querying {lang}.wikipedia.org for '{title}': {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"  Error parsing response for '{title}': {e}")
        return None

class ProgressTracker:
    """Track and save progress for resumable processing."""
    
    def __init__(self, output_file: Path, progress_file: Path):
        self.output_file = output_file
        self.progress_file = progress_file
        self.processed_ids = set()
        self.results = []
        self.should_exit = False
        self.qid_cache = {}  # Cache for URL -> QID mappings
        
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
            existing_data = load_json(self.output_file)
            if isinstance(existing_data, list):
                self.results = existing_data
                # Track which flickr_ids have been processed
                for item in self.results:
                    self.processed_ids.add(item.get('flickr_id'))
                print(f"Loaded {len(self.results)} existing results")
        
        # Load progress tracking file
        if self.progress_file.exists():
            progress_data = load_json(self.progress_file)
            self.qid_cache = progress_data.get('qid_cache', {})
            print(f"Loaded cache with {len(self.qid_cache)} URL->QID mappings")
    
    def save_progress(self):
        """Save current progress to files."""
        # Save the results
        save_json(self.results, self.output_file)
        
        # Save progress tracking
        progress_data = {
            'qid_cache': self.qid_cache,
            'processed_count': len(self.processed_ids),
            'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        save_json(progress_data, self.progress_file)
    
    def is_processed(self, flickr_id: str) -> bool:
        """Check if a flickr_id has already been processed."""
        return flickr_id in self.processed_ids
    
    def add_result(self, result: dict):
        """Add a processed result."""
        self.results.append(result)
        self.processed_ids.add(result['flickr_id'])
    
    def get_cached_qid(self, url: str) -> Optional[str]:
        """Get cached QID for a URL."""
        return self.qid_cache.get(url)
    
    def cache_qid(self, url: str, qid: str):
        """Cache a QID for a URL."""
        self.qid_cache[url] = qid

def process_wiki_links(photo_data: dict, tracker: ProgressTracker, session: requests.Session) -> dict:
    """
    Process wiki links for a photo to extract Wikidata QIDs.
    """
    result = {
        'flickr_id': photo_data['flickr_id'],
        'hdl_url': photo_data.get('hdl_url'),
        'wiki_references': []
    }
    
    for ref in photo_data.get('wiki_references', []):
        processed_ref = {
            'type': ref['type'],
            'author': ref['author'],
            'wiki_links': ref['wiki_links'],
            'wikidata': []
        }
        
        # Keep only the text field if it's a note (shorter)
        if ref['type'] == 'note':
            processed_ref['text'] = ref.get('text', '')
        
        # Process each wiki link
        qids = []
        for url in ref['wiki_links']:
            # Check cache first
            cached_qid = tracker.get_cached_qid(url)
            if cached_qid:
                qids.append(cached_qid)
                continue
            
            # Check if it's a Wikidata URL
            if 'wikidata.org' in url:
                qid = extract_qid_from_wikidata_url(url)
                if qid:
                    qids.append(qid)
                    tracker.cache_qid(url, qid)
            
            # Check if it's a Wikipedia URL
            elif 'wikipedia.org' in url:
                parsed = parse_wikipedia_url(url)
                if parsed:
                    lang, title = parsed
                    qid = get_wikidata_qid_from_wikipedia(lang, title, session)
                    if qid:
                        qids.append(qid)
                        tracker.cache_qid(url, qid)
                    # Small delay to be polite to Wikipedia API
                    time.sleep(0.1)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_qids = []
        for qid in qids:
            if qid not in seen:
                seen.add(qid)
                unique_qids.append(qid)
        
        processed_ref['wikidata'] = unique_qids
        result['wiki_references'].append(processed_ref)
    
    return result

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    input_file = base_dir / 'data' / 'wiki_links.json'
    output_file = base_dir / 'data' / 'wiki_links_expanded.json'
    progress_file = base_dir / 'data' / '.wiki_expansion_progress.json'
    
    print("Loading wiki_links.json...")
    wiki_data = load_json(input_file)
    
    if not wiki_data:
        print("No wiki links data found!")
        return
    
    # Initialize progress tracker
    tracker = ProgressTracker(output_file, progress_file)
    
    # Filter out already processed items
    items_to_process = [item for item in wiki_data if not tracker.is_processed(item.get('flickr_id', ''))]
    
    if not items_to_process:
        print("\nAll items have already been processed!")
        return
    
    print(f"\nProcessing {len(items_to_process)} items (skipping {len(wiki_data) - len(items_to_process)} already processed)...")
    print("Press Ctrl+C to stop and save progress at any time.\n")
    
    # Create session with custom user agent
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'data script user: thisismattmiller'
    })
    
    # Process each item
    save_interval = 10  # Save every 10 items
    
    for i, item in enumerate(items_to_process, 1):
        if tracker.should_exit:
            break
        
        flickr_id = item.get('flickr_id', 'unknown')
        print(f"[{i}/{len(items_to_process)}] Processing flickr_id: {flickr_id}")
        
        # Process wiki links
        result = process_wiki_links(item, tracker, session)
        tracker.add_result(result)
        
        # Count QIDs found
        qid_count = sum(len(ref['wikidata']) for ref in result['wiki_references'])
        if qid_count > 0:
            print(f"  Found {qid_count} Wikidata QIDs")
        
        # Save progress periodically
        if i % save_interval == 0:
            tracker.save_progress()
            print(f"  [Progress saved: {len(tracker.results)} items processed]")
    
    # Final save
    tracker.save_progress()
    
    # Print summary
    print("\n" + "="*60)
    print("WIKIDATA EXPANSION SUMMARY")
    print("="*60)
    print(f"Total items in input: {len(wiki_data)}")
    print(f"Items processed: {len(tracker.results)}")
    print(f"Unique URL->QID mappings cached: {len(tracker.qid_cache)}")
    
    # Count total QIDs
    total_qids = sum(
        len(ref['wikidata']) 
        for item in tracker.results 
        for ref in item['wiki_references']
    )
    print(f"Total Wikidata QIDs extracted: {total_qids}")
    
    if tracker.should_exit:
        remaining = len(items_to_process) - (len(tracker.results) - (len(wiki_data) - len(items_to_process)))
        print(f"\nStopped early. {remaining} items remaining to process.")
        print("Run the script again to continue from where you left off.")
    else:
        print("\nAll items processed successfully!")
        print(f"Results saved to: {output_file}")
        
        # Clean up progress file when complete
        if progress_file.exists():
            progress_file.unlink()
            print("Progress tracking file cleaned up.")
    
    print("="*60)

if __name__ == "__main__":
    main()