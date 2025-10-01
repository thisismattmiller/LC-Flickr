#!/usr/bin/env python3
"""
Build a GEXF (Graph Exchange XML Format) file from wiki_links_relationships_only.json
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path


def write_gexf(gexf_elem, output_file):
    """Write GEXF element to file with proper formatting."""
    # Create the tree and write with proper declaration
    tree = ET.ElementTree(gexf_elem)
    ET.indent(tree, space="    ")  # Format with indentation
    tree.write(output_file, encoding='UTF-8', xml_declaration=True)


def extract_qid_from_index(index_val):
    """Extract QID from index value like 'p:P1654_wd:Q2251569'"""
    parts = index_val.split('_')
    if len(parts) >= 2 and 'wd:' in parts[1]:
        return parts[1].replace('wd:', '')  # Return just Q2251569
    return None


def extract_property_from_index(index_val):
    """Extract property from index value like 'p:P1654_wd:Q2251569'"""
    parts = index_val.split('_')
    if len(parts) >= 1 and 'p:' in parts[0]:
        return parts[0]  # Keep as p:P1654 for lookup
    return None


def main():
    # Define paths
    input_file = Path(__file__).parent.parent / 'data' / 'wiki_links_relationships_only.json'
    label_lookup_file = Path(__file__).parent.parent / 'data' / 'wikidata_label_lookup.json'
    output_file = Path(__file__).parent.parent / 'data' / 'wiki_graph.gexf'
    
    # Load the data
    print(f"Loading data from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} items")
    
    # Load label lookup
    print(f"Loading label lookup from {label_lookup_file}...")
    try:
        with open(label_lookup_file, 'r', encoding='utf-8') as f:
            label_lookup = json.load(f)
        print(f"Loaded {len(label_lookup)} labels")
    except FileNotFoundError:
        print("Warning: Label lookup file not found, will use IDs only")
        label_lookup = {}
    
    # Create GEXF structure with proper namespaces
    gexf_attribs = {
        'version': '1.2',
        'xmlns': 'http://www.gexf.net/1.2draft',
        'xmlns:viz': 'http://www.gexf.net/1.2/viz',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsi:schemaLocation': 'http://www.gexf.net/1.2draft http://www.gexf.net/1.2draft/gexf.xsd'
    }
    gexf = ET.Element('gexf', **gexf_attribs)
    graph = ET.SubElement(gexf, 'graph', mode="static", defaultedgetype="directed")
    
    # Add attributes definition for edges (optional - uncomment if you want p-number attribute)
    # attributes = ET.SubElement(graph, 'attributes', **{'class': 'edge'})
    # ET.SubElement(attributes, 'attribute', id="0", title="p-number", type="string")
    
    nodes_elem = ET.SubElement(graph, 'nodes')
    edges_elem = ET.SubElement(graph, 'edges')
    
    # Track nodes and edges we've created
    created_nodes = set()
    created_edges = set()  # Track (source, target, label) tuples to avoid duplicates
    edge_id = 0
    
    # Process each item (limit to first 500 for performance)
    for item in data[:500]:
    # for item in data:        
        flickr_id = item.get('flickr_id')
        hdl_url = item.get('hdl_url', '')
        
        if not flickr_id:
            continue
        
        # Process wiki references
        for ref in item.get('wiki_references', []):
            for wikidata_item in ref.get('wikidata_data', []):
                # Get the QID for this wikidata item
                qid = wikidata_item.get('qid')
                if not qid:
                    continue
                
                # Create merged image-wikidata node
                merged_node_id = f"image_{flickr_id}_{qid}"
                if merged_node_id not in created_nodes:
                    # Use wikidata label from lookup, fallback to QID if not found
                    lookup_key = f"wd:{qid}"
                    wikidata_label = label_lookup.get(lookup_key, qid)
                    # Debug: print if label not found
                    if wikidata_label == qid:
                        print(f"Warning: No label found for {lookup_key}, using QID {qid}")
                    node = ET.SubElement(nodes_elem, 'node', id=merged_node_id, label=wikidata_label)
                    created_nodes.add(merged_node_id)
                
                # Process index values (relationships)
                for index_val in wikidata_item.get('index', []):
                    # Extract QID from index
                    index_qid = extract_qid_from_index(index_val)
                    property_id = extract_property_from_index(index_val)
                    
                    if not index_qid or not property_id:
                        continue
                    
                    # Create node for the related entity if not exists  
                    if index_qid not in created_nodes:
                        label = label_lookup.get(f"wd:{index_qid}", index_qid)
                        node = ET.SubElement(nodes_elem, 'node', id=index_qid, label=label)
                        created_nodes.add(index_qid)
                    
                    # Create edge from merged node to related entity (check for duplicates)
                    property_label = label_lookup.get(property_id, property_id)
                    edge_key = (merged_node_id, index_qid, property_label)
                    if edge_key not in created_edges:
                        edge = ET.SubElement(edges_elem, 'edge', 
                                             id=str(edge_id), 
                                             source=merged_node_id, 
                                             target=index_qid,
                                             weight="1",
                                             label=property_label)
                        created_edges.add(edge_key)
                        
                        # Add p-number attribute (optional - uncomment if you want it)
                        # attvalues = ET.SubElement(edge, 'attvalues')
                        # ET.SubElement(attvalues, 'attvalue', **{'for': '0', 'value': property_id.replace('p:', '')})
                        
                        edge_id += 1
    
    # Write the GEXF file
    print(f"Writing GEXF file to {output_file}...")
    write_gexf(gexf, output_file)
    
    print(f"Done! Created graph with {len(created_nodes)} nodes and {edge_id} edges")
    
    # Print statistics
    image_nodes = sum(1 for n in created_nodes if n.startswith('image_'))
    entity_nodes = len(created_nodes) - image_nodes
    print(f"  - Image nodes: {image_nodes}")
    print(f"  - Entity nodes: {entity_nodes}")


if __name__ == '__main__':
    main()