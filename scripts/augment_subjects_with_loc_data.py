#!/usr/bin/env python3
"""
Augment subject_tag_mappings.json with Library of Congress authority data.

For each subject, queries the LOC Suggest API to retrieve:
- Authority URI
- Variant labels (alternate forms of the subject heading)
"""

import json
import time
import urllib.parse
import urllib.request
import ssl
from pathlib import Path


def query_loc_api(subject_term):
    """
    Query LOC Suggest API for a subject term.
    Returns (uri, variant_labels) or (None, []) if not found.
    """
    # URL encode the subject term
    encoded_term = urllib.parse.quote(subject_term)
    url = f"https://id.loc.gov/authorities/subjects/suggest2?q={encoded_term}"

    try:
        # Create SSL context that doesn't verify certificates
        # (needed for some Python installations)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Make the request
        with urllib.request.urlopen(url, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))

        # Check if we have hits
        hits = data.get('hits', [])
        if not hits:
            return None, []

        # Get the first hit (best match)
        first_hit = hits[0]

        # Extract URI
        uri = first_hit.get('uri', None)

        # Extract variant labels from 'more' section
        more = first_hit.get('more', {})
        variant_labels = more.get('variantLabels', [])

        return uri, variant_labels

    except Exception as e:
        print(f"  Error querying API for '{subject_term}': {e}")
        return None, []


def main():
    # Set up paths
    base_dir = Path(__file__).parent.parent
    input_file = base_dir / 'apps' / 'lcsh_vs_tags' / 'subject_tag_mappings.json'
    output_file = base_dir / 'apps' / 'lcsh_vs_tags' / 'subject_tag_mappings.json'

    print("Loading subject_tag_mappings.json...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    mappings = data.get('mappings', [])
    print(f"Found {len(mappings)} subjects to process")

    print("\nQuerying LOC API for each subject...")
    print("(This may take a few minutes due to rate limiting)")

    augmented_count = 0
    not_found_count = 0

    for i, mapping in enumerate(mappings, 1):
        subject = mapping['subject']

        # Query the API
        uri, variant_labels = query_loc_api(subject)

        # Add to mapping
        mapping['loc_authority'] = {
            'uri': uri,
            'variant_labels': variant_labels
        }

        if uri:
            augmented_count += 1
            status = f"✓ Found (URI: {uri}, {len(variant_labels)} variants)"
        else:
            not_found_count += 1
            status = "✗ Not found"

        print(f"  [{i}/{len(mappings)}] {subject[:60]:<60} {status}")

        # Rate limiting: be respectful to the API
        # Wait 0.5 seconds between requests
        time.sleep(0.5)

    # Save augmented data
    print(f"\nSaving augmented data to {output_file.name}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "="*80)
    print("AUGMENTATION COMPLETE")
    print("="*80)
    print(f"Total subjects processed: {len(mappings)}")
    print(f"Successfully augmented: {augmented_count}")
    print(f"Not found in LOC: {not_found_count}")
    print(f"\nAugmented data saved to: {output_file}")
    print("="*80)


if __name__ == '__main__':
    main()