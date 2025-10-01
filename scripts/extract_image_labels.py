#!/usr/bin/env python3
"""
Extract Flickr IDs from GEXF network file nodes and match with titles from metadata.
"""

import xml.etree.ElementTree as ET
import json
from pathlib import Path
import re


def extract_flickr_ids_from_gexf(gexf_file):
    """
    Extract Flickr IDs from GEXF file nodes that have image_ prefix.

    Returns:
        set: Unique Flickr IDs found in the file
    """
    tree = ET.parse(gexf_file)
    root = tree.getroot()

    flickr_ids = set()

    # Find all nodes regardless of namespace
    # First try with common namespaces
    nodes = root.findall('.//{http://www.gexf.net/1.2draft}node')
    if not nodes:
        nodes = root.findall('.//{http://gexf.net/1.3}node')
    if not nodes:
        # Fallback to no namespace
        nodes = root.findall('.//node')

    print(f"Found {len(nodes)} nodes in GEXF file")

    for node in nodes:
        node_id = node.get('id', '')

        # Extract Flickr ID from image_*_Q* format
        if node_id.startswith('image_'):
            # Pattern: image_FLICKRID_QNUMBER
            match = re.match(r'image_(\d+)_Q\d+', node_id)
            if match:
                flickr_id = match.group(1)
                flickr_ids.add(flickr_id)

    return flickr_ids


def load_flickr_metadata(metadata_file):
    """
    Load Flickr metadata and create a lookup dictionary.

    Returns:
        dict: Mapping of Flickr ID to title
    """
    with open(metadata_file, 'r', encoding='utf-8') as f:
        photos = json.load(f)

    # Create lookup dictionary
    id_to_title = {}
    for photo in photos:
        photo_id = photo.get('id', '')
        title = photo.get('title', '')
        if photo_id:
            id_to_title[photo_id] = title

    return id_to_title


def main():
    # Define paths
    gexf_file = Path(__file__).parent.parent / 'data' / 'network_layout.gexf'
    metadata_file = Path(__file__).parent.parent / 'data' / 'flickr_photos_with_metadata.json'
    output_file = Path(__file__).parent.parent / 'apps' / 'graph' / 'data' / 'image_labels.json'

    # Check if input files exist
    if not gexf_file.exists():
        print(f"Error: GEXF file {gexf_file} does not exist!")
        return

    if not metadata_file.exists():
        print(f"Error: Metadata file {metadata_file} does not exist!")
        return

    print(f"Loading GEXF file from {gexf_file}...")

    # Extract Flickr IDs from GEXF
    flickr_ids = extract_flickr_ids_from_gexf(gexf_file)
    print(f"Found {len(flickr_ids)} unique Flickr IDs in GEXF file")

    if not flickr_ids:
        print("No Flickr IDs found in the file")
        return

    # Sample of Flickr IDs found
    print(f"Sample Flickr IDs: {list(flickr_ids)[:5]}")

    # Load Flickr metadata
    print(f"\nLoading Flickr metadata from {metadata_file}...")
    metadata_lookup = load_flickr_metadata(metadata_file)
    print(f"Loaded {len(metadata_lookup)} photos from metadata")

    # Match Flickr IDs with titles
    image_labels = {}
    matched_count = 0
    unmatched = []

    for flickr_id in flickr_ids:
        if flickr_id in metadata_lookup:
            image_labels[flickr_id] = metadata_lookup[flickr_id]
            matched_count += 1
        else:
            # Use the ID itself as a fallback
            image_labels[flickr_id] = f"Image {flickr_id}"
            unmatched.append(flickr_id)

    print(f"\nMatched {matched_count} Flickr IDs with titles")
    if unmatched:
        print(f"Could not find titles for {len(unmatched)} IDs (using ID as fallback)")
        print(f"Sample unmatched: {unmatched[:5]}")

    # Sample of matched labels
    sample_items = list(image_labels.items())[:5]
    print("\nSample image labels:")
    for flickr_id, title in sample_items:
        # Truncate long titles for display
        display_title = title[:60] + "..." if len(title) > 60 else title
        print(f"  {flickr_id}: {display_title}")

    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save to JSON file (minified)
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(image_labels, f, ensure_ascii=False, separators=(',', ':'))

    print(f"Successfully saved {len(image_labels)} image labels to {output_file}")

    # Verify file size
    if output_file.exists():
        file_size = output_file.stat().st_size / 1024  # Size in KB
        print(f"Output file size: {file_size:.2f} KB")


if __name__ == '__main__':
    main()