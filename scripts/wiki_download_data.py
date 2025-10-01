#!/usr/bin/env python3
"""
Download Wikidata statements for QIDs from wiki_links_expanded.json
Build index and label lookups for analysis.
"""

import json
import requests
import time
import signal
from pathlib import Path
from typing import Dict, List, Set, Optional
from collections import defaultdict
import re

def load_json(file_path: Path) -> any:
    """Load JSON data from a file."""
    if not file_path.exists():
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: any, file_path: Path) -> None:
    """Save data to a JSON file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def extract_unique_qids(data: List[dict]) -> Set[str]:
    """Extract all unique QIDs from the expanded wiki data."""
    qids = set()
    for item in data:
        for ref in item.get('wiki_references', []):
            for qid in ref.get('wikidata', []):
                if qid and qid.startswith('Q'):
                    qids.add(qid)
    return qids

def query_wikidata_sparql(qid: str, session: requests.Session) -> Optional[dict]:
    """
    Query Wikidata SPARQL endpoint for statements about a QID.
    """
    sparql_query = f"""
    SELECT ?wdLabel ?p ?ps_ ?ps_Label {{
        VALUES (?entity) {{(wd:{qid})}}

        ?entity ?p ?statement .
        ?statement ?ps ?ps_ .
        
        ?wd wikibase:claim ?p.
        ?wd wikibase:statementProperty ?ps.
        ?wd wikibase:propertyType ?dataType .

        OPTIONAL {{
          ?statement ?pq ?pq_ .
          ?wdpq wikibase:qualifier ?pq .
        }}
        FILTER (?dataType != wikibase:ExternalId)
        SERVICE wikibase:label {{
          bd:serviceParam wikibase:language "en, [AUTO_LANGUAGE]" .            
        }}
    }} ORDER BY ?wd ?statement ?ps_
    """
    
    endpoint_url = "https://query.wikidata.org/sparql"
    
    try:
        response = session.get(
            endpoint_url,
            params={'query': sparql_query, 'format': 'json'},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"  Error querying Wikidata for {qid}: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"  Error parsing response for {qid}: {e}")
        return None

def extract_property_id(uri: str) -> str:
    """Extract property ID (P123) from URI."""
    match = re.search(r'/prop/(P\d+)', uri)
    if match:
        return match.group(1)
    return uri

def extract_entity_id(uri: str) -> str:
    """Extract entity ID (Q123) from URI."""
    match = re.search(r'/entity/(Q\d+)', uri)
    if match:
        return match.group(1)
    return uri

def process_sparql_results(qid: str, results: dict, label_lookup: dict) -> dict:
    """
    Process SPARQL results to extract statements and build index.
    """
    processed = {
        'qid': qid,
        'statements': [],
        'index': []
    }
    
    if not results or 'results' not in results:
        return processed
    
    bindings = results.get('results', {}).get('bindings', [])
    
    for binding in bindings:
        # Extract property info
        prop_uri = binding.get('p', {}).get('value', '')
        prop_id = extract_property_id(prop_uri)
        prop_label = binding.get('wdLabel', {}).get('value', '')
        
        # Extract value info
        value_data = binding.get('ps_', {})
        value_type = value_data.get('type', '')
        value = value_data.get('value', '')
        value_label = binding.get('ps_Label', {}).get('value', '')
        
        # Create statement record
        statement = {
            'property': prop_id,
            'property_label': prop_label,
            'value': value,
            'value_type': value_type,
            'value_label': value_label
        }
        processed['statements'].append(statement)
        
        # Add to label lookup
        if prop_id and prop_label:
            label_lookup[f"p:{prop_id}"] = prop_label
        
        # Build index string
        if value_type == 'uri' and '/entity/' in value:
            # It's a Wikidata entity
            entity_id = extract_entity_id(value)
            index_str = f"p:{prop_id}_wd:{entity_id}"
            processed['index'].append(index_str)
            
            # Add entity to label lookup
            if entity_id and value_label:
                label_lookup[f"wd:{entity_id}"] = value_label
        elif value_type == 'literal':
            # For literals, we might want to handle differently
            # For now, just track the property
            index_str = f"p:{prop_id}_literal"
            if index_str not in processed['index']:
                processed['index'].append(index_str)
    
    return processed

class ProgressTracker:
    """Track and save progress for resumable processing."""
    
    def __init__(self, output_file: Path, label_file: Path, progress_file: Path, qid_cache_file: Path):
        self.output_file = output_file
        self.label_file = label_file
        self.progress_file = progress_file
        self.qid_cache_file = qid_cache_file
        self.processed_qids = set()
        self.results = []
        self.label_lookup = {}
        self.qid_data_cache = {}  # Cache for QID -> data mapping
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
        # Load QID data cache
        if self.qid_cache_file.exists():
            self.qid_data_cache = load_json(self.qid_cache_file)
            print(f"Loaded QID data cache with {len(self.qid_data_cache)} entries")
            # Add cached QIDs to processed set
            self.processed_qids.update(self.qid_data_cache.keys())
        
        # Load existing output file
        if self.output_file.exists():
            existing_data = load_json(self.output_file)
            if isinstance(existing_data, list):
                self.results = existing_data
                print(f"Loaded {len(self.results)} existing results")
        
        # Load existing label lookup
        if self.label_file.exists():
            self.label_lookup = load_json(self.label_file)
            print(f"Loaded label lookup with {len(self.label_lookup)} entries")
        
        # Load progress tracking
        if self.progress_file.exists():
            progress_data = load_json(self.progress_file)
            saved_qids = progress_data.get('processed_qids', [])
            self.processed_qids.update(saved_qids)
            print(f"Loaded progress: {len(self.processed_qids)} QIDs processed")
    
    def save_progress(self, wiki_data=None):
        """Save current progress to files."""
        # Save QID data cache
        save_json(self.qid_data_cache, self.qid_cache_file)
        
        # If we have wiki_data, rebuild the complete output
        if wiki_data:
            self.results = build_output_structure(wiki_data, self.qid_data_cache)
        
        # Save the results
        save_json(self.results, self.output_file)
        
        # Save label lookup
        save_json(self.label_lookup, self.label_file)
        
        # Save progress tracking
        progress_data = {
            'processed_qids': list(self.processed_qids),
            'processed_count': len(self.processed_qids),
            'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        save_json(progress_data, self.progress_file)
    
    def is_processed(self, qid: str) -> bool:
        """Check if a QID has already been processed."""
        return qid in self.processed_qids
    
    def add_qid_data(self, qid: str, data: dict):
        """Mark a QID as processed and store its data."""
        self.processed_qids.add(qid)
        self.qid_data_cache[qid] = data

def build_output_structure(wiki_data: List[dict], qid_data_cache: Dict[str, dict]) -> List[dict]:
    """Build the complete output structure with QID data."""
    output_data = []
    
    for item in wiki_data:
        new_item = {
            'flickr_id': item['flickr_id'],
            'hdl_url': item.get('hdl_url'),
            'wiki_references': []
        }
        
        for ref in item.get('wiki_references', []):
            new_ref = {
                'type': ref['type'],
                'author': ref['author'],
                'wiki_links': ref['wiki_links'],
                'wikidata': ref.get('wikidata', []),
                'wikidata_data': []
            }
            
            # Add data for each QID
            for qid in ref.get('wikidata', []):
                if qid in qid_data_cache:
                    new_ref['wikidata_data'].append(qid_data_cache[qid])
                else:
                    # QID not yet processed, add placeholder
                    new_ref['wikidata_data'].append({
                        'qid': qid,
                        'statements': [],
                        'index': []
                    })
            
            new_item['wiki_references'].append(new_ref)
        
        output_data.append(new_item)
    
    return output_data

def main():
    # Define paths
    base_dir = Path(__file__).parent.parent
    input_file = base_dir / 'data' / 'wiki_links_expanded.json'
    output_file = base_dir / 'data' / 'wiki_links_expanded_with_data.json'
    label_file = base_dir / 'data' / 'wikidata_label_lookup.json'
    progress_file = base_dir / 'data' / '.wiki_data_download_progress.json'
    qid_cache_file = base_dir / 'data' / '.wiki_qid_data_cache.json'
    
    print("Loading wiki_links_expanded.json...")
    wiki_data = load_json(input_file)
    
    if not wiki_data:
        print("No expanded wiki data found!")
        return
    
    # Extract all unique QIDs
    print("Extracting unique QIDs...")
    all_qids = extract_unique_qids(wiki_data)
    print(f"Found {len(all_qids)} unique QIDs")
    
    # Initialize progress tracker
    tracker = ProgressTracker(output_file, label_file, progress_file, qid_cache_file)
    
    # Filter out already processed QIDs
    qids_to_process = [qid for qid in all_qids if not tracker.is_processed(qid)]
    
    if not qids_to_process:
        print("\nAll QIDs have already been processed!")
        print("Building final output with all cached data...")
        # Build and save the complete structure with cached data
        tracker.results = build_output_structure(wiki_data, tracker.qid_data_cache)
        tracker.save_progress(wiki_data)
    else:
        print(f"\nProcessing {len(qids_to_process)} QIDs (skipping {len(all_qids) - len(qids_to_process)} already processed)...")
        print("Press Ctrl+C to stop and save progress at any time.\n")
        
        # Create session with custom user agent
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'thisismattmiller user'
        })
        
        # Download data for each QID
        save_interval = 10
        
        for i, qid in enumerate(qids_to_process, 1):
            if tracker.should_exit:
                break
            
            print(f"[{i}/{len(qids_to_process)}] Processing {qid}...")
            
            # Query Wikidata
            results = query_wikidata_sparql(qid, session)
            
            if results:
                # Process results
                processed = process_sparql_results(qid, results, tracker.label_lookup)
                tracker.add_qid_data(qid, processed)
                
                # Show summary
                stmt_count = len(processed['statements'])
                index_count = len(processed['index'])
                print(f"  Found {stmt_count} statements, {index_count} indexed relationships")
            else:
                # Mark as processed even if failed
                empty_data = {'qid': qid, 'statements': [], 'index': []}
                tracker.add_qid_data(qid, empty_data)
                print(f"  No data retrieved for {qid}")
            
            # Rate limiting
            time.sleep(0.5)
            
            # Save periodically
            if i % save_interval == 0:
                print(f"  [Saving progress: {len(tracker.processed_qids)} QIDs processed]")
                tracker.save_progress(wiki_data)
        
        # Final save with complete structure
        print("\nBuilding final output structure...")
        tracker.save_progress(wiki_data)
    
    # Print summary
    print("\n" + "="*60)
    print("WIKIDATA DOWNLOAD SUMMARY")
    print("="*60)
    print(f"Total unique QIDs: {len(all_qids)}")
    print(f"QIDs processed: {len(tracker.processed_qids)}")
    print(f"Label lookup entries: {len(tracker.label_lookup)}")
    
    # Count statements
    total_statements = 0
    total_indexed = 0
    for qid_data in tracker.qid_data_cache.values():
        total_statements += len(qid_data.get('statements', []))
        total_indexed += len(qid_data.get('index', []))
    
    print(f"Total statements retrieved: {total_statements}")
    print(f"Total indexed relationships: {total_indexed}")
    
    if tracker.should_exit and len(qids_to_process) > 0:
        remaining = len(qids_to_process) - len(tracker.processed_qids)
        print(f"\nStopped early. {remaining} QIDs remaining to process.")
        print("Run the script again to continue from where you left off.")
    else:
        print("\nAll QIDs processed successfully!")
        print(f"Results saved to: {output_file}")
        print(f"Label lookup saved to: {label_file}")
        
        # Clean up progress files when complete
        if progress_file.exists():
            progress_file.unlink()
            print("Progress tracking file cleaned up.")
        if qid_cache_file.exists():
            qid_cache_file.unlink()
            print("QID cache file cleaned up.")
    
    print("="*60)

if __name__ == "__main__":
    main()