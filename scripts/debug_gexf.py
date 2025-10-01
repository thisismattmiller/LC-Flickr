#!/usr/bin/env python3
"""
Debug GEXF parsing to see what's happening with node extraction.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import re


def debug_gexf_parsing(gexf_file):
    """
    Debug GEXF file parsing to understand node extraction issues.
    """
    tree = ET.parse(gexf_file)
    root = tree.getroot()

    print(f"Root tag: {root.tag}")
    print(f"Root attrib: {root.attrib}")

    # Try different ways to find nodes
    methods = [
        ('.//node', 'No namespace'),
        ('.//{http://www.gexf.net/1.2draft}node', 'GEXF 1.2 namespace'),
        ('.//{http://gexf.net/1.3}node', 'GEXF 1.3 namespace'),
    ]

    for xpath, description in methods:
        nodes = root.findall(xpath)
        print(f"\n{description}: Found {len(nodes)} nodes")

        if nodes:
            print("First 5 nodes:")
            for i, node in enumerate(nodes[:5]):
                node_id = node.get('id', '')
                print(f"  {i+1}. id='{node_id}'")
            break

    # Also check the structure
    print("\nDirect children of root:")
    for child in root:
        print(f"  {child.tag}")
        if 'graph' in child.tag.lower():
            print("  Direct children of graph:")
            for grandchild in child:
                print(f"    {grandchild.tag}")
                if 'nodes' in grandchild.tag.lower():
                    # Count direct children
                    node_count = len(list(grandchild))
                    print(f"      Number of direct children: {node_count}")

    # Let's also check with a simple regex on the file content
    print("\nRegex search for Q-IDs in file:")
    with open(gexf_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all node IDs
    node_pattern = r'<node[^>]+id="([^"]+)"'
    node_ids = re.findall(node_pattern, content)
    print(f"Total node IDs found via regex: {len(node_ids)}")

    # Extract Q-IDs
    qids = set()
    for node_id in node_ids:
        if node_id.startswith('Q') and node_id[1:].isdigit():
            qids.add(node_id)
        elif 'image_' in node_id:
            match = re.search(r'Q\d+', node_id)
            if match:
                qids.add(match.group())

    print(f"Unique Q-IDs found: {len(qids)}")
    print(f"Sample Q-IDs: {list(qids)[:10]}")


if __name__ == '__main__':
    input_file = Path(__file__).parent.parent / 'data' / 'wiki_graph.gexf'

    if not input_file.exists():
        print(f"Error: {input_file} does not exist!")
    else:
        debug_gexf_parsing(input_file)