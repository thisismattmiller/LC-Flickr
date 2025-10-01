#!/usr/bin/env python3
"""
Extract Q-IDs from GEXF network file and fetch their labels from Wikidata.
"""

import xml.etree.ElementTree as ET
import json
import requests
import time
from pathlib import Path
import re


def extract_qids_from_gexf(gexf_file):
    """
    Extract Q-IDs from GEXF file nodes.

    Returns:
        set: Unique Q-IDs found in the file
    """
    tree = ET.parse(gexf_file)
    root = tree.getroot()

    qids = set()

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

        # Extract Q-ID from the node ID
        # Pattern: either direct Q-ID or image_*_Q-ID format
        if node_id.startswith('Q') and node_id[1:].isdigit():
            qids.add(node_id)
        elif 'image_' in node_id:
            # Extract Q-ID from image_*_Q#### format
            match = re.search(r'Q\d+', node_id)
            if match:
                qids.add(match.group())

    return qids


def fetch_wikidata_labels(qids, batch_size=500):
    """
    Fetch labels and instance_of values for Q-IDs from Wikidata SPARQL endpoint in batches.

    Args:
        qids: Set of Q-IDs to fetch labels for
        batch_size: Number of Q-IDs to fetch per request

    Returns:
        dict: Mapping of Q-ID to dict with 'label' and 'instance_of' keys
    """
    qid_list = list(qids)
    results = {}

    # Initialize all Q-IDs with default values
    for qid in qid_list:
        results[qid] = {
            'label': qid,  # Default to Q-ID if no label found
            'instance_of': None  # Default to None if no P31 found
        }

    # Wikidata SPARQL endpoint
    sparql_url = "https://query.wikidata.org/sparql"

    # Custom User-Agent header
    headers = {
        'User-Agent': 'user: thisismattmiller - data scripts',
        'Accept': 'application/json'
    }

    for i in range(0, len(qid_list), batch_size):
        batch = qid_list[i:i + batch_size]

        # Create SPARQL query for batch
        # Format Q-IDs for SPARQL (wd:Q123 format)
        qid_values = ' '.join([f'wd:{qid}' for qid in batch])

        # Query for both label and instance_of (P31)
        # Using OPTIONAL to get results even if P31 doesn't exist
        # Using LIMIT 1 in subquery to get only first instance_of value
        sparql_query = f"""
        SELECT ?item ?itemLabel ?instanceOf ?instanceOfLabel WHERE {{
          VALUES ?item {{ {qid_values} }}
          OPTIONAL {{
            ?item wdt:P31 ?instanceOf .
          }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """

        params = {
            'query': sparql_query,
            'format': 'json'
        }

        try:
            print(f"Fetching batch {i//batch_size + 1}/{(len(qid_list) + batch_size - 1)//batch_size}...")
            response = requests.get(sparql_url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            # Extract labels and instance_of from SPARQL response
            if 'results' in data and 'bindings' in data['results']:
                # Group results by Q-ID since there might be multiple rows per item (multiple P31 values)
                item_data = {}

                for binding in data['results']['bindings']:
                    if 'item' in binding:
                        # Extract Q-ID from the URI
                        qid = binding['item']['value'].split('/')[-1]

                        # Initialize if not seen before
                        if qid not in item_data:
                            item_data[qid] = {
                                'label': binding.get('itemLabel', {}).get('value', qid),
                                'instance_of_list': []
                            }

                        # Add instance_of if present
                        if 'instanceOf' in binding and 'instanceOfLabel' in binding:
                            instance_of_qid = binding['instanceOf']['value'].split('/')[-1]
                            instance_of_label = binding['instanceOfLabel']['value']
                            # Store both Q-ID and label for instance_of
                            item_data[qid]['instance_of_list'].append({
                                'qid': instance_of_qid,
                                'label': instance_of_label
                            })

                # Update results with fetched data
                for qid, data_dict in item_data.items():
                    results[qid]['label'] = data_dict['label']
                    # Take first instance_of if any exist
                    if data_dict['instance_of_list']:
                        results[qid]['instance_of'] = data_dict['instance_of_list'][0]
                    else:
                        results[qid]['instance_of'] = None

            print(f"  Batch {i//batch_size + 1}: Processed {len(batch)} items, total items: {len(results)}")

            # Be nice to the SPARQL endpoint
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching batch starting at {i}: {e}")
            # Keep default values for failed batch

    return results


def main():
    # Define paths
    input_file = Path(__file__).parent.parent / 'data' / 'network_layout.gexf'
    output_file = Path(__file__).parent.parent / 'apps' / 'graph' / 'data' / 'node_labels.json'

    # Check if input file exists
    if not input_file.exists():
        print(f"Error: Input file {input_file} does not exist!")
        return

    print(f"Loading GEXF file from {input_file}...")

    # Extract Q-IDs
    qids = extract_qids_from_gexf(input_file)
    print(f"Found {len(qids)} unique Q-IDs")

    if not qids:
        print("No Q-IDs found in the file")
        return

    # Sample of Q-IDs found
    print(f"Sample Q-IDs: {list(qids)[:5]}")

    # Fetch labels and instance_of from Wikidata
    print("\nFetching labels and instance_of from Wikidata...")
    results = fetch_wikidata_labels(qids)

    print(f"Successfully fetched data for {len(results)} items")

    # Sample of fetched data
    sample_items = list(results.items())[:5]
    print("\nSample data:")
    for qid, data in sample_items:
        instance_of_str = f"{data['instance_of']['label']} ({data['instance_of']['qid']})" if data['instance_of'] else "None"
        print(f"  {qid}: {data['label']} | instance_of: {instance_of_str}")

    # Create output directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save to JSON file (minified)
    print(f"\nSaving to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, separators=(',', ':'))

    print(f"Successfully saved data for {len(results)} items to {output_file}")

    # Verify file size
    if output_file.exists():
        file_size = output_file.stat().st_size / 1024  # Size in KB
        print(f"Output file size: {file_size:.2f} KB")


if __name__ == '__main__':
    main()