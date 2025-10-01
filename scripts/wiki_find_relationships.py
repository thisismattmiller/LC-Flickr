#!/usr/bin/env python3
"""
Find items in wiki_links_expanded_with_data.json that share index values with other items.
"""

import json
import copy
from collections import defaultdict
from pathlib import Path


def find_relationships(data):
    """
    Find items that share index values with at least one other item.
    Only considers index values containing 'wd:Q' (Wikidata entities), 
    ignoring literal values.
    
    Returns:
        Tuple of (list of items with shared values, dict of shared indices with counts)
    """
    # Build index lookup: index_value -> list of (item_idx, flickr_id)
    index_lookup = defaultdict(list)
    
    # First pass: collect all index values and their associated items
    for item_idx, item in enumerate(data):
        flickr_id = item.get('flickr_id')
        if not flickr_id:
            continue
            
        wiki_refs = item.get('wiki_references', [])
        for ref_idx, ref in enumerate(wiki_refs):
            wikidata_data_list = ref.get('wikidata_data', [])
            for wd_idx, wikidata_item in enumerate(wikidata_data_list):
                index_values = wikidata_item.get('index', [])
                for index_val in index_values:
                    # Only consider values with wd:Q (Wikidata entities)
                    # Skip literal values
                    if 'wd:Q' in index_val and '_literal' not in index_val:
                        index_lookup[index_val].append((item_idx, ref_idx, wd_idx, flickr_id))
    
    # Second pass: identify items with shared index values and count shared relationships
    items_with_relationships = {}  # item_idx -> set of shared index values
    shared_indices = {}
    
    for index_val, item_list in index_lookup.items():
        # If this index value appears in more than one item
        if len(item_list) > 1:
            # Track this shared relationship
            shared_indices[index_val] = len(item_list)
            # Add all items that share this index value
            for item_idx, ref_idx, wd_idx, _ in item_list:
                if item_idx not in items_with_relationships:
                    items_with_relationships[item_idx] = defaultdict(lambda: defaultdict(set))
                items_with_relationships[item_idx][ref_idx][wd_idx].add(index_val)
    
    # Extract the actual items that have relationships and filter their index arrays
    result = []
    for item_idx in sorted(items_with_relationships.keys()):
        item = copy.deepcopy(data[item_idx])  # Deep copy to avoid modifying nested structures
        
        # Filter index arrays to only include shared values
        for ref_idx, ref in enumerate(item.get('wiki_references', [])):
            for wd_idx, wikidata_item in enumerate(ref.get('wikidata_data', [])):
                if ref_idx in items_with_relationships[item_idx] and wd_idx in items_with_relationships[item_idx][ref_idx]:
                    # Replace index with only the shared values, ensuring uniqueness
                    shared_vals = items_with_relationships[item_idx][ref_idx][wd_idx]
                    wikidata_item['index'] = sorted(list(shared_vals))
                else:
                    # Clear index if no shared values for this wikidata item
                    wikidata_item['index'] = []
        
        result.append(item)
    
    return result, shared_indices


def main():
    # Define paths
    input_file = Path(__file__).parent.parent / 'data' / 'wiki_links_expanded_with_data.json'
    original_file = Path(__file__).parent.parent / 'data' / 'wiki_links.json'
    output_file = Path(__file__).parent.parent / 'data' / 'wiki_links_relationships_only.json'
    label_lookup_file = Path(__file__).parent.parent / 'data' / 'wikidata_label_lookup.json'
    
    # Load the expanded data
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} items")
    
    # Load the original data to get author_id, date, text fields
    print(f"Loading original data from {original_file}...")
    with open(original_file, 'r', encoding='utf-8') as f:
        original_data = json.load(f)
    print(f"Loaded {len(original_data)} original items")
    
    # Create a lookup for original data by flickr_id
    original_lookup = {item['flickr_id']: item for item in original_data}
    
    # Load label lookup
    print(f"Loading label lookup from {label_lookup_file}...")
    try:
        with open(label_lookup_file, 'r', encoding='utf-8') as f:
            label_lookup = json.load(f)
        print(f"Loaded {len(label_lookup)} labels")
    except FileNotFoundError:
        print("Warning: Label lookup file not found, will use IDs only")
        label_lookup = {}
    
    # Find items with relationships
    print("Finding items with shared index values...")
    related_items, shared_indices = find_relationships(data)
    
    print(f"Found {len(related_items)} items with relationships")
    print(f"Found {len(shared_indices)} unique shared relationships")
    
    # Merge in the original data fields (author_id, date, text)
    print("Merging original data fields...")
    for item in related_items:
        flickr_id = item.get('flickr_id')
        if flickr_id in original_lookup:
            original_item = original_lookup[flickr_id]
            # Update wiki_references with original fields
            for i, ref in enumerate(item.get('wiki_references', [])):
                if i < len(original_item.get('wiki_references', [])):
                    orig_ref = original_item['wiki_references'][i]
                    # Add missing fields from original
                    if 'author_id' in orig_ref:
                        ref['author_id'] = orig_ref['author_id']
                    if 'date' in orig_ref:
                        ref['date'] = orig_ref['date']
                    if 'text' in orig_ref:
                        ref['text'] = orig_ref['text']
    
    # Save the results
    print(f"Saving results to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(related_items, f, indent=2, ensure_ascii=False)
    
    print("Done!")
    
    # Print some statistics
    if related_items:
        # Count unique index values in the results
        all_indices = set()
        for item in related_items:
            for ref in item.get('wiki_references', []):
                for wd_data in ref.get('wikidata_data', []):
                    all_indices.update(wd_data.get('index', []))
        
        print(f"\nStatistics:")
        print(f"  - Items with relationships: {len(related_items)}")
        print(f"  - Unique index values in results: {len(all_indices)}")
        
        # Print top 100 most common shared relationships
        print(f"\nTop 100 most common shared relationships:")
        print("-" * 80)
        
        # Sort by count (descending) and get top 100
        sorted_shared = sorted(shared_indices.items(), key=lambda x: x[1], reverse=True)[:100]
        
        for rank, (index_val, count) in enumerate(sorted_shared, 1):
            # Parse the index value to extract property and entity
            parts = index_val.split('_')
            if len(parts) >= 2:
                prop = parts[0]  # Keep as p:P###
                entity = parts[1]  # Keep as wd:Q###
                
                # Get labels from lookup (keys already have p: and wd: prefixes)
                prop_label = label_lookup.get(prop, prop)
                entity_label = label_lookup.get(entity, entity)
                
                print(f"{rank:3}. {index_val:50} - {count:4} items")
                print(f"     Property: {prop} ({prop_label})")
                print(f"     Entity: {entity} ({entity_label})")
            else:
                print(f"{rank:3}. {index_val:50} - {count:4} items")


if __name__ == '__main__':
    main()